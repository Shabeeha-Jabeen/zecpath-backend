from locust import HttpUser, task, between


class ZecPathUser(HttpUser):
    wait_time = between(10, 15)

    @task(3)
    def list_jobs(self):
        self.client.get("/api/jobs/", name="GET /api/jobs/")

    @task(1)
    def featured_jobs(self):
        self.client.get("/api/jobs/featured/", name="GET /api/jobs/featured/")

    @task(1)
    def latest_jobs(self):
        self.client.get("/api/jobs/latest/", name="GET /api/jobs/latest/")
