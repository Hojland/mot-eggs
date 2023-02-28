terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.54.0"
    }
  }
}

provider "google" {
  credentials = var.GOOGLE_CREDENTIALS
}

provider "google-beta" {
  credentials = var.GOOGLE_CREDENTIALS
}
