import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct
import os


class AlbPriorityPocStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        allowed_ip_cidr = cdk.CfnParameter(
            self,
            "AllowedIpCidr",
            type="String",
            description="CIDR block allowed to reach the ALB on port 80 (for example 203.0.113.10/32)",
            allowed_pattern=r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])/(3[0-2]|[12]?[0-9])$",
            constraint_description="Must be a valid IPv4 CIDR block.",
        )

        vpc = ec2.Vpc(self, "Vpc", max_azs=2, nat_gateways=0)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        image_asset = ecr_assets.DockerImageAsset(
            self,
            "AppImage",
            directory=os.path.join(os.path.dirname(__file__), "..", "testapp"),
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        # Create task definition with explicit Fargate launch type
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            memory_limit_mib=512,
            cpu=256,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.X86_64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )
        
        task_definition.add_container(
            "AppContainer",
            image=ecs.ContainerImage.from_docker_image_asset(image_asset),
            memory_limit_mib=512,
            port_mappings=[ecs.PortMapping(container_port=80)],
        )

        # Create ALB
        load_balancer = elbv2.ApplicationLoadBalancer(
            self,
            "ALB",
            vpc=vpc,
            internet_facing=True,
        )

        # Create Fargate service with explicit launch type
        service_construct = ecs.FargateService(
            self,
            "FargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )
        
        # Create listener
        listener = load_balancer.add_listener(
            "Listener",
            port=80,
            open=False,
        )
        
        listener.add_targets(
            "ServiceTarget",
            port=80,
            targets=[service_construct],
        )
        
        # service = type('obj', (object,), {
        #     'load_balancer': load_balancer,
        #     'service': service_construct,
        # })()
        
        # Allow only specific IP to reach the ALB
        load_balancer.connections.allow_from(
            ec2.Peer.ipv4(allowed_ip_cidr.value_as_string),
            ec2.Port.tcp(80),
        )

        # Fargate tasks only accept traffic from the ALB security group
        service_construct.connections.allow_from(
            load_balancer.connections,
            ec2.Port.tcp(80),
        )
