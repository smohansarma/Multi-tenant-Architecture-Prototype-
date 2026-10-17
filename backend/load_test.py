
import asyncio
import aiohttp
import time

BASE_URL = "http://127.0.0.1:8000/api/"
LOGIN_URL = BASE_URL + "login/"
EMPLOYEE_URL = BASE_URL + "employee/"

USER_COUNT = 1000
CONCURRENCY = 100

USERS = [
    {
        "identifier": f"loadtest{i}@example.com",
        "password": "LoadTest123!",
        "expected_tenant": f"vsuite_tenant_{i:04d}",
    }
    for i in range(USER_COUNT)
]


async def login(session, user, semaphore):
    async with semaphore:
        try:
            async with session.post(
                LOGIN_URL,
                json={
                    "identifier": user["identifier"],
                    "password": user["password"],
                },
            ) as response:
                if response.status != 200:
                    return {
                        "user": user,
                        "token": None,
                        "error": f"Login failed: HTTP {response.status}",
                    }

                data = await response.json()

                return {
                    "user": user,
                    "token": data.get("token"),
                    "error": None,
                }

        except Exception as exc:
            return {
                "user": user,
                "token": None,
                "error": str(exc),
            }


async def hit_employee(session, user, token, semaphore):
    start = time.perf_counter()

    async with semaphore:
        try:
            async with session.get(
                EMPLOYEE_URL,
                headers={"Authorization": f"Bearer {token}"},
            ) as response:
                data = await response.json()
                elapsed = time.perf_counter() - start

                actual_tenant = data.get("tenant_db")
                expected_tenant = user["expected_tenant"]

                return {
                    "correct": (
                        response.status == 200
                        and actual_tenant == expected_tenant
                    ),
                    "mismatch": (
                        response.status == 200
                        and actual_tenant != expected_tenant
                    ),
                    "elapsed": elapsed,
                    "user": user["identifier"],
                    "expected": expected_tenant,
                    "actual": actual_tenant,
                    "status": response.status,
                }

        except Exception as exc:
            return {
                "correct": False,
                "mismatch": False,
                "elapsed": time.perf_counter() - start,
                "user": user["identifier"],
                "expected": user["expected_tenant"],
                "actual": None,
                "status": "ERROR",
                "error": str(exc),
            }


async def main():
    timeout = aiohttp.ClientTimeout(total=60)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)

    login_semaphore = asyncio.Semaphore(50)
    request_semaphore = asyncio.Semaphore(CONCURRENCY)

    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
    ) as session:

        print(f"Logging in {USER_COUNT} unique users...")

        login_results = await asyncio.gather(
            *[
                login(session, user, login_semaphore)
                for user in USERS
            ]
        )

        valid_logins = [
            item for item in login_results
            if item["token"]
        ]

        login_failures = [
            item for item in login_results
            if not item["token"]
        ]

        print(f"Successful logins: {len(valid_logins)}")
        print(f"Failed logins: {len(login_failures)}")

        if login_failures:
            for item in login_failures[:10]:
                print("LOGIN FAILED:", item["user"]["identifier"],
                      item["error"])

        print("Sending one employee request per authenticated user...")

        start = time.perf_counter()

        results = await asyncio.gather(
            *[
                hit_employee(
                    session,
                    item["user"],
                    item["token"],
                    request_semaphore,
                )
                for item in valid_logins
            ]
        )

        total_time = time.perf_counter() - start

    successful = sum(r["correct"] for r in results)
    failed = len(results) - successful
    mismatches = sum(r["mismatch"] for r in results)

    durations = sorted(r["elapsed"] for r in results)
    p95 = durations[min(len(durations) - 1, int(len(durations) * 0.95))] \
        if durations else 0

    print("\n========== LOAD TEST RESULTS ==========")
    print(f"Unique test users: {USER_COUNT}")
    print(f"Successful logins: {len(valid_logins)}")
    print(f"Failed logins: {len(login_failures)}")
    print(f"Employee requests: {len(results)}")
    print(f"Concurrency limit: {CONCURRENCY}")
    print(f"Successful requests: {successful}")
    print(f"Failed or incorrect requests: {failed}")
    print(f"Tenant mismatches: {mismatches}")
    print(f"Total request time: {total_time:.2f} seconds")

    if total_time > 0:
        print(f"Throughput: {len(results) / total_time:.2f} requests/sec")

    print(f"Approx. p95 response time: {p95 * 1000:.2f} ms")

    for result in results:
        if not result["correct"]:
            print("REQUEST FAILED:", result)


if __name__ == "__main__":
    asyncio.run(main())
