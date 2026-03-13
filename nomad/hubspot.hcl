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
        image = "lleans/hubspot-company:latest"
        ports = ["http"]
        force_pull = true
	dns_servers = ["${attr.unique.network.ip-address}"]
        dns_search_domains = ["service.consul"]
      }

      env {
	  DATABASE_URL = "postgresql://hubspot:hubspot123@postgres.service.consul:5432/hubspot_db"
          PORT = "3012"
          LOG_LEVEL = "INFO"
          MAX_WORKER_THREADS = "5"
          FLASK_ENV = "staging"
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
