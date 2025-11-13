terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "shadower-terraform-state"
    key    = "analytics/terraform.tfstate"
    region = "us-west-2"
    encrypt = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Shadower-Analytics"
      ManagedBy   = "Terraform"
      Environment = var.environment
    }
  }
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"

  environment = var.environment
  vpc_cidr    = var.vpc_cidr
  azs         = var.availability_zones
}

# RDS Instance for Analytics
resource "aws_db_subnet_group" "analytics" {
  name       = "shadower-analytics-${var.environment}"
  subnet_ids = module.vpc.private_subnet_ids

  tags = {
    Name        = "shadower-analytics-db-subnet-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_security_group" "analytics_db" {
  name        = "shadower-analytics-db-${var.environment}"
  description = "Security group for Analytics PostgreSQL database"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "PostgreSQL from EKS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [module.vpc.eks_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "shadower-analytics-db-sg-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_db_instance" "analytics" {
  identifier     = "shadower-analytics-${var.environment}"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_encrypted     = true
  storage_type          = "gp3"
  iops                  = var.db_iops

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.analytics_db.id]
  db_subnet_group_name   = aws_db_subnet_group.analytics.name

  backup_retention_period = var.backup_retention_period
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  multi_az               = var.environment == "production" ? true : false
  deletion_protection    = var.environment == "production" ? true : false
  skip_final_snapshot    = var.environment != "production"
  final_snapshot_identifier = var.environment == "production" ? "shadower-analytics-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60
  monitoring_role_arn            = aws_iam_role.rds_monitoring.arn

  performance_insights_enabled    = true
  performance_insights_retention_period = 7

  tags = {
    Name        = "shadower-analytics-db-${var.environment}"
    Environment = var.environment
  }
}

# ElastiCache for Redis
resource "aws_elasticache_subnet_group" "analytics" {
  name       = "shadower-analytics-cache-${var.environment}"
  subnet_ids = module.vpc.private_subnet_ids

  tags = {
    Name        = "shadower-analytics-cache-subnet-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_security_group" "analytics_cache" {
  name        = "shadower-analytics-cache-${var.environment}"
  description = "Security group for Analytics Redis cache"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "Redis from EKS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [module.vpc.eks_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "shadower-analytics-cache-sg-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_elasticache_replication_group" "analytics" {
  replication_group_id       = "shadower-analytics-${var.environment}"
  replication_group_description = "Redis cache for Shadower Analytics"

  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.redis_node_type
  number_cache_clusters = var.redis_num_cache_nodes
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.analytics.name
  security_group_ids = [aws_security_group.analytics_cache.id]

  automatic_failover_enabled = var.redis_num_cache_nodes > 1 ? true : false
  multi_az_enabled          = var.environment == "production" ? true : false

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled        = true
  auth_token                = var.redis_auth_token

  snapshot_retention_limit = var.redis_snapshot_retention_limit
  snapshot_window         = "02:00-03:00"
  maintenance_window      = "sun:03:00-sun:04:00"

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format      = "json"
    log_type        = "slow-log"
  }

  tags = {
    Name        = "shadower-analytics-cache-${var.environment}"
    Environment = var.environment
  }
}

# S3 Bucket for Exports
resource "aws_s3_bucket" "exports" {
  bucket = "shadower-analytics-exports-${var.environment}"

  tags = {
    Name        = "Analytics Exports - ${var.environment}"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "exports" {
  bucket = aws_s3_bucket.exports.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "exports" {
  bucket = aws_s3_bucket.exports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id

  rule {
    id     = "delete-old-exports"
    status = "Enabled"

    expiration {
      days = var.export_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_public_access_block" "exports" {
  bucket = aws_s3_bucket.exports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM Role for RDS Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "shadower-analytics-rds-monitoring-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "shadower-analytics-rds-monitoring-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/shadower-analytics-${var.environment}/slow-log"
  retention_in_days = 30

  tags = {
    Name        = "shadower-analytics-redis-slow-log-${var.environment}"
    Environment = var.environment
  }
}

# Outputs
output "db_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.analytics.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.analytics.primary_endpoint_address
  sensitive   = true
}

output "s3_exports_bucket" {
  description = "S3 bucket for exports"
  value       = aws_s3_bucket.exports.id
}
