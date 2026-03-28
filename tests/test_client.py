from __future__ import annotations

from more_socrata import MoreSocrata

def check_client():
    obj = MoreSocrata(domain="data.cityofnewyork.us",
                      domain_id="NYC")
    print(obj.ALL_AGENCIES)

if __name__ == "__main__":
    check_client()