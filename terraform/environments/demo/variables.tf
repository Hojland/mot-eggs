variable "GOOGLE_CREDENTIALS" {
  type      = string
  sensitive = true
}

variable "project_name" {
  type        = string
  description = "name of gcp project"
}

variable "billing_account" {
  type        = string
  description = "who is the investor?"
}

variable "project_id" {
  description = "Unique project id"
  type        = string
}