global_user_map = {
    "mohan@gmail.com":{
        "emp_id": 1,
        "password": "mohan123",
        "tenant_db": "vsuite_company_A",
        "role":"Administrator"
    },
    "arun@gmail.com": {
        "emp_id": 2,
        "password": "arun123",
        "tenant_db": "vsuite_company_B",
        "role": "Employee",
    } 
}

for i in range(1000):
    email = f"loadtest{i}@example.com"

    global_user_map[email] = {
        "emp_id": 1000 + i,
        "password": "LoadTest123!",
        "tenant_db": f"vsuite_tenant_{i:04d}",
        "role": "Employee",
    }