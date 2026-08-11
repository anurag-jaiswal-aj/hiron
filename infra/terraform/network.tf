# AWS Network Routing & NAT Architecture

# 1. Internet Gateway (Required for Public Subnets & NAT)
resource "aws_internet_gateway" "production" {
  vpc_id = aws_vpc.production.id

  tags = {
    Name = "hiron-production-igw"
  }
}

# 2. Public Route Table (Routing to IGW)
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.production.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.production.id
  }

  tags = {
    Name = "hiron-prod-public-rt"
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# 3. NAT Gateway (For Private Subnet Egress)
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = {
    Name = "hiron-prod-nat-eip"
  }
}

resource "aws_nat_gateway" "production" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_a.id

  tags = {
    Name = "hiron-production-nat"
  }

  # Ensure IGW exists before creating NAT Gateway
  depends_on = [aws_internet_gateway.production]
}

# 4. Private Route Table (Routing to NAT Gateway)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.production.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.production.id
  }

  tags = {
    Name = "hiron-prod-private-rt"
  }
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}
