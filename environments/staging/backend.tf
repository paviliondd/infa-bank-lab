terraform {
  backend "s3" {
    # Tên bucket cố định do mình tạo trong MinIO
    bucket = "terraform-states-bank"
    key    = "staging/network-infra.tfstate"
    region = "ap-southeast-1" # Giá trị giả định để API bot aws-sdk hoạt động

    # Điểm truy cập của MinIO trên VPS 5
    # Sửa HTTP/HTTPS và IP khớp với thực tế config của bạn (Vd: k8s-worker2)
    endpoints = {
      s3 = "http://103.110.85.124:9000"
    }

    # Custom endpoint routing (chỉ dành cho MinIO local)
    use_path_style = true
    
    # Validation skip: MinIO không phải máy chủ Amazon S3
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
  }
}
