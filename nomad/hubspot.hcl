job "hubspot-company" {
  datacenters = ["dc1"]
  type        = "service"

  group "app" {
    count = 1

    network {
      port "http" {
        static = 3012
      }
    }

    task "hubspot-company" {
      driver = "docker"

      config {
        image = "YOUR_DOCKERHUB_USERNAME/hubspot-company:latest"
        ports = ["http"]
        force_pull = true
      }

      env {
        PORT         = "3012"
        LOG_LEVEL    = "INFO"
        DATABASE_URL = "postgresql://hubspot:hubspot123@${attr.unique.network.ip-address}:5432/hubspot_db"
      }

      resources {
        cpu    = 300
        memory = 384
      }

      service {
        name = "hubspot-company"
        port = "http"
        tags = ["flask", "api", "hubspot"]

        check {
          type     = "http"
          path     = "/scan/health"
          interval = "10s"
          timeout  = "3s"
        }
      }
    }
  }
}
