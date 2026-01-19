variable "credentials" {
  description = "My credentials"
  default     = "./keys/my-creds-gcp.json"
}

variable "project" {
  description = "GCP Project ID"
  default     = "terraform-484619"
}

variable "region" {
  description = "GCP Region"
  default     = "europe-west1"
}

variable "location" {
  description = "Project Location"
  default     = "EU"
}

variable "bq_dataset_name" {
  description = "My BigQuery Dataset Name"
  default     = "demo_dataset"
}

variable "gcs_bucket_name" {
  description = "My Storage Bucket Storage Name"
  default     = "terraform-484619-terra-bucket"
}

variable "gcs_storage_class" {
  description = "Bucket Storage Class"
  default     = "STANDARD"
}