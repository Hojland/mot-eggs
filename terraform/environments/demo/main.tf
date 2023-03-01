locals {
  netherlands_id          = "europe-west4"
  netherlands_id_specific = "europe-west4-a"
  cluster_name            = "demo"
}


# Unique to my situation. You don't need to make a folder and put that folder_id to the google_project
resource "google_folder" "demo" {
  display_name = var.project_name
  parent       = "folders/435823098599" 
}

resource "google_project" "demo" {
  name                = var.project_name
  project_id          = var.project_id
  billing_account     = var.billing_account
  folder_id           = google_folder.demo.folder_id
  auto_create_network = false
}

resource "google_project_iam_custom_role" "host_project_network_security_admin" {
  project     = var.project_id
  role_id     = "host_project_network_security_admin"
  title       = "Host Project Network and Security Admin"
  description = "This role allows to administer network and security of the host project. Intended for use by GKE automation on service projects."
  permissions = [
    "compute.firewalls.create",
    "compute.firewalls.delete",
    "compute.firewalls.get",
    "compute.firewalls.list",
    "compute.firewalls.update",
    "compute.networks.updatePolicy"
  ]
}

resource "google_container_registry" "registry" {
  project  = var.project_id
  location = "EU"
}

# Project services
resource "google_project_service" "container" {
  project = google_project.demo.project_id
  service = "container.googleapis.com"
}

resource "google_project_service" "compute" {
  project = google_project.demo.project_id
  service = "compute.googleapis.com"
}

resource "google_project_service" "vpcaccess" {
  project = google_project.demo.project_id
  service = "vpcaccess.googleapis.com"
}

# VPC
resource "google_compute_network" "vpc" {
  name                    = "vpc"
  project                 = google_project.demo.project_id
  routing_mode            = "GLOBAL"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "default" {
  project       = google_project.demo.project_id
  name          = format("default-%s", local.netherlands_id)
  ip_cidr_range = "10.10.0.0/20"
  region        = local.netherlands_id
  network       = google_compute_network.vpc.id

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 1
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

resource "google_compute_subnetwork" "demo" {
  project       = google_project.demo.project_id
  name          = format("demo-%s", local.netherlands_id)
  ip_cidr_range = "10.2.0.0/16"
  region        = local.netherlands_id
  network       = google_compute_network.vpc.id

  secondary_ip_range {
    range_name    = "pod"
    ip_cidr_range = "10.0.0.0/16"
  }

  secondary_ip_range {
    range_name    = "svc"
    ip_cidr_range = "10.1.0.0/16"
  }

  log_config {
    aggregation_interval = "INTERVAL_10_MIN"
    flow_sampling        = 1
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cluster and nodepool
resource "google_service_account" "demo" {
  account_id   = "cluster-sa-demo"
  project      = google_project.demo.project_id
  display_name = "Demo GKE Service Account"
}

resource "google_storage_bucket_iam_member" "viewer" {
  bucket = google_container_registry.registry.id
  role = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.demo.email}"
}

resource "google_container_cluster" "demo" {
  name                     = local.cluster_name
  location                 = local.netherlands_id_specific
  project                  = google_project.demo.project_id
  remove_default_node_pool = true
  initial_node_count       = 1

  subnetwork               = google_compute_subnetwork.demo.self_link
  network                  = google_compute_network.vpc.self_link

  ip_allocation_policy {
    cluster_secondary_range_name  = google_compute_subnetwork.demo.secondary_ip_range[0].range_name
    services_secondary_range_name = google_compute_subnetwork.demo.secondary_ip_range[1].range_name
  }

  # node_config {
  #   disk_size_gb = 100
  #   disk_type = "pd-standard"
  # }

  workload_identity_config {
    workload_pool = "${google_project.demo.project_id}.svc.id.goog"
  }


  depends_on = [google_project_service.compute,
    google_project_service.container,
    google_project_iam_member.compute_networkuser_container,
    google_project_iam_member.compute_networkuser_cloudservices,
    google_project_iam_binding.container_hostServiceAgent]
}

resource "google_container_node_pool" "node_pool_1" {
  name               = "demo-node-pool-1"
  location           = local.netherlands_id_specific
  cluster            = google_container_cluster.demo.name
  project            = google_project.demo.project_id
  initial_node_count = 1
  autoscaling {
    min_node_count = 1
    max_node_count = 2
  }
  node_config {
    machine_type    = "c2d-standard-4"
    service_account = google_service_account.demo.email
    disk_size_gb    = 50
    oauth_scopes    = ["storage-ro", "https://www.googleapis.com/auth/logging.write", "https://www.googleapis.com/auth/monitoring"]

  }
  lifecycle {
    create_before_destroy = true
  }
}


resource "google_project_iam_member" "compute_networkuser_cloudservices" {
  project = google_project.demo.project_id
  role    = "roles/compute.networkUser"
  member  = "serviceAccount:${format("%s@cloudservices.gserviceaccount.com", google_project.demo.number)}"
}

resource "google_project_iam_member" "compute_networkuser_container" {
  project = google_project.demo.project_id
  role    = "roles/compute.networkUser"
  member  = "serviceAccount:${format("service-%s@container-engine-robot.iam.gserviceaccount.com", google_project.demo.number)}"
}

  resource "google_project_iam_binding" "container_hostServiceAgent" {
  project = google_project.demo.project_id
  role    = "roles/container.hostServiceAgentUser"
  members = [
    "serviceAccount:${format("service-%s@container-engine-robot.iam.gserviceaccount.com", google_project.demo.number)}",
    "serviceAccount:${format("%s@cloudservices.gserviceaccount.com", google_project.demo.number)}",
  ]
}


# Allow GKE to auto configure firewall rules for load balancer health checks
resource "google_project_iam_binding" "vpc_network_security_admin" {
  project = google_project.demo.project_id
  role    = "projects/${google_project.demo.project_id}/roles/host_project_network_security_admin"
  members = [
    "serviceAccount:${format("service-%s@container-engine-robot.iam.gserviceaccount.com", google_project.demo.number)}"
  ]
}


resource "google_service_account" "k8s_deploy" {
  account_id   = "k8s-deploy-service-account"
  project      = google_project.demo.project_id
  display_name = "K8S Deployment Service Account"
}


data "google_iam_policy" "k8s_deploy" {
  binding {
    role = "roles/container.admin"
    members = [
      "serviceAccount:${google_service_account.k8s_deploy.email}",
    ]
  }
  binding {
    role = "roles/container.clusterViewer"
    members = [
      "serviceAccount:${google_service_account.k8s_deploy.email}",
    ]
  }

  binding {
    role = "roles/storage.objectViewer"
    members = [
      "serviceAccount:${google_service_account.k8s_deploy.email}",
    ]
  }

  depends_on = [
    google_service_account.k8s_deploy
  ]
}