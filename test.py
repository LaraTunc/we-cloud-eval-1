import boto3
from botocore.config import Config

session = boto3.Session(profile_name='lara-private')

my_config = Config(
    region_name = 'us-east-1',
    signature_version = 'v4',
)

client = boto3.client('ec2', config=my_config)

# All resources to be in us-east-1
# VPC 
response = client.create_vpc(
    CidrBlock='10.0.0.0/24',
    TagSpecifications=[
        {
            'ResourceType': 'vpc',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Eval-1-vpc'
                },
                {
                    'Key': 'project',
                    'Value': 'wecloud'
                },
            ]
        },
    ]
)
vpcId = response.get('Vpc').get('VpcId')
print(f"Created vpc id",vpcId)

# Internet gateway
response = client.create_internet_gateway(
    TagSpecifications=[
        {
            'ResourceType': 'internet-gateway',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Eval-1-ig'
                },
                {
                    'Key': 'project',
                    'Value': 'wecloud'
                },
            ]
        },
    ]
)
internetGatewayId = response.get('InternetGateway').get('InternetGatewayId')
print(f"Created internet gateway id",response.get('InternetGateway').get('InternetGatewayId'))

# attach internet gateway to VPC 
response = client.attach_internet_gateway(
    InternetGatewayId=internetGatewayId,
    VpcId=vpcId
)

# Public subnet 
response = client.create_subnet(
    CidrBlock='10.0.0.0/28', 
    VpcId=vpcId, 
    TagSpecifications=[
        {
            'ResourceType': 'subnet',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Eval-1-subnet'
                },
                {
                    'Key': 'project',
                    'Value': 'wecloud'
                },
            ]
        },
    ]
)
subnetId = response.get('Subnet').get('SubnetId')
print(f"Created public subnet id",subnetId)

# Enable auto-assign public IP on public subnet 
response = client.modify_subnet_attribute(
    SubnetId=subnetId,
    MapPublicIpOnLaunch={'Value': True}
)

# Public route table for public subnet 
response = client.create_route_table(
    VpcId=vpcId,
    TagSpecifications=[
        {
            'ResourceType': 'route-table',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Eval-1-rt'
                },
                {
                    'Key': 'project',
                    'Value': 'wecloud'
                },
            ]
        },
    ]
)
routeTableId = response.get('RouteTable').get('RouteTableId') 
print(f"Created public route table id",routeTableId)

# Route table has a routing rule to internet gateway
response = client.create_route(
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=internetGatewayId,
    RouteTableId=routeTableId,
)
print(f"Created route table rule to internet gateway")

# Associate the public subnet with the public route table 
response = client.associate_route_table(
    RouteTableId=routeTableId,
    SubnetId=subnetId,
)
print(f"Associated public subnet with public route table")

# Security group for EC2 instances 
response = client.create_security_group(
    Description='Eval-1-sg',
    GroupName='Eval-1-sg',
    VpcId=vpcId,
    TagSpecifications=[
        {
            'ResourceType': 'security-group',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'Eval-1-sg'
                },
                {
                    'Key': 'project',
                    'Value': 'wecloud'
                },
            ]
        },
    ]
) 
securityGroupId = response.get('GroupId') 
print(f"Created security group id",securityGroupId)

# Inbound rule for SSH access to EC2 instances 
response = client.authorize_security_group_ingress(
    GroupId=securityGroupId,
    IpPermissions=[
        {
            'FromPort': 22,
            'IpProtocol': 'tcp',
            'IpRanges': [
                {
                    'CidrIp': '0.0.0.0/0',
                    'Description': 'SSH access',
                },
            ],
            'ToPort': 22,
        },
         {
            'FromPort': 80,
            'IpProtocol': 'tcp',
            'IpRanges': [
                {
                    'CidrIp': '0.0.0.0/0',
                    'Description': 'HTTP access',
                },
            ],
            'ToPort': 80,
        },
    ],
)
print(f"Created inbound rule for SSH access to EC2 instances")

# EC2 instances 
user_data = """#!/bin/bash

# Update system packages
sudo apt-get update

# Install Python 3.10
sudo apt-get install -y python3.10

# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Java 11
sudo apt-get install -y openjdk-11-jdk

# Install Docker Engine
sudo apt-get install -y docker.io

# Install Nginx to test internet connection
sudo apt install nginx
"""

instances_info = [
    {'imageId': 'ami-06aa3f7caf3a30282', 'instanceType': 't2.small', 'name': 'master-node-01'},
    {'imageId': 'ami-06aa3f7caf3a30282', 'instanceType': 't2.micro', 'name': 'worker-node-01'},
    {'imageId': 'ami-06aa3f7caf3a30282', 'instanceType': 't2.micro', 'name': 'worker-node-02'}
]

for instance in instances_info:
    response = client.run_instances(
        ImageId=instance.get('imageId'),
        InstanceType=instance.get('instanceType'),
        KeyName='lara-us-east-1',
        MaxCount=1,
        MinCount=1,
        SecurityGroupIds=[
            securityGroupId,
        ],
        SubnetId=subnetId,
        UserData=user_data,
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': instance.get('name'),
                    },
                    {
                        'Key': 'project',
                        'Value': 'wecloud',
                    },
                ],
            },
        ],
    )
    print(f"Created instance",response.get('Instances')[0].get('InstanceId'))

# All three EC2 instances are
# Are reachable to each other - e.g. via the ping command
# Are accessible remotely by SSH

