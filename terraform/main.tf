terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "Name of the S3 bucket (must be globally unique across all of AWS)"
  type        = string
  default     = "kyc-api-documents-mumbai-123" # Start fresh with a new bucket name
}

variable "key_name" {
  description = "Name of an existing AWS Key Pair to allow SSH access to the EC2 instance"
  type        = string
}

variable "db_password" {
  description = "Password for the RDS PostgreSQL database"
  type        = string
  sensitive   = true
}

# 1. Create the Private S3 Bucket
resource "aws_s3_bucket" "kyc_bucket" {
  bucket = var.bucket_name
}

# Block all public access to the bucket (Security Best Practice)
resource "aws_s3_bucket_public_access_block" "kyc_bucket_access" {
  bucket                  = aws_s3_bucket.kyc_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 2. Create the IAM User for the API
resource "aws_iam_user" "api_user" {
  name = "kyc_api_service_account"
}

# Generate Access Keys for the User
resource "aws_iam_access_key" "api_user_key" {
  user = aws_iam_user.api_user.name
}

# 3. Attach AWS Textract Permissions
resource "aws_iam_user_policy_attachment" "textract_access" {
  user       = aws_iam_user.api_user.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonTextractFullAccess"
}

# 4. Create and Attach Scoped S3 Permissions
resource "aws_iam_user_policy" "s3_access" {
  name = "kyc_api_s3_access"
  user = aws_iam_user.api_user.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.kyc_bucket.arn,
          "${aws_s3_bucket.kyc_bucket.arn}/*"
        ]
      }
    ]
  })
}

# 5. Get the Default VPC
data "aws_vpc" "default" {
  default = true
}

# 6. Create Security Groups
resource "aws_security_group" "ec2_sg" {
  name        = "kyc_api_ec2_sg"
  description = "Allow HTTP, HTTPS, and SSH inbound traffic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # In production, consider restricting to your own IP!
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "kyc_api_rds_sg"
  description = "Allow PostgreSQL traffic only from the EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "PostgreSQL from EC2"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 7. Find the latest Ubuntu 22.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 8. Create the EC2 Instance
resource "aws_instance" "app_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t2.micro" # Free-tier eligible
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  tags = {
    Name = "KYC-API-Server"
  }
}

# 9. Create the RDS PostgreSQL Database
resource "aws_db_instance" "postgres_db" {
  identifier             = "kyc-api-db"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "14"
  instance_class         = "db.t3.micro" # Free-tier eligible
  db_name                = "kyc_db"
  username               = "postgres"
  password               = var.db_password
  parameter_group_name   = "default.postgres14"
  skip_final_snapshot    = true          # Allows terraform destroy without waiting for backups
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible    = false         # Keeps database off the public internet!
}

# 10. Output variables for easy access
output "AWS_REGION" {
  value = var.aws_region
}

output "S3_BUCKET_NAME" {
  value = aws_s3_bucket.kyc_bucket.id
}

output "AWS_ACCESS_KEY_ID" {
  value = aws_iam_access_key.api_user_key.id
}

output "AWS_SECRET_ACCESS_KEY" {
  value     = aws_iam_access_key.api_user_key.secret
  sensitive = true
}

output "EC2_PUBLIC_IP" {
  value = aws_instance.app_server.public_ip
}

output "RDS_DATABASE_URL" {
  value = "postgresql://postgres:${var.db_password}@${aws_db_instance.postgres_db.endpoint}/kyc_db"
  sensitive = true
}