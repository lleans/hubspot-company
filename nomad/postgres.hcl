job "postgres" {
  datacenters = ["dc1"]
  type        = "service"

  group "db" {
    count = 1

    network {
      port "db" {
        static = 5432
      }
    }

    volume "postgres_data" {
      type      = "host"
      read_only = false
      source    = "postgres_data"
    }

    task "postgres" {
      driver = "docker"

      config {
        image = "postgres:15-alpine"
        ports = ["db"]
      }

      volume_mount {
        volume      = "postgres_data"
        destination = "/var/lib/postgresql/data"
        read_only   = false
      }

      env {
        POSTGRES_DB       = "hubspot_db"
        POSTGRES_USER     = "hubspot"
        POSTGRES_PASSWORD = "hubspot123"
      }

      resources {
        cpu    = 200
        memory = 256
      }

      service {
        name = "postgres"
        port = "db"

        check {
          type     = "tcp"
          interval = "10s"
          timeout  = "3s"
        }
      }
    }
  }
}
