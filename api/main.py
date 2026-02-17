import os
import psycopg2
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Agri Geo Monitoring API", version="0.1.0")

def get_conn():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5434")),
        dbname=os.getenv("PGDATABASE", "agri_geo"),
        user=os.getenv("PGUSER", "agri"),
        password=os.getenv("PGPASSWORD", "agri"),
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/risk/{parcel_id}")
def latest_risk(parcel_id: str):
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT run_id, parcel_id, ndvi_t0, ndvi_t1, variation_pct, risk_score, created_at
            FROM geo.parcel_runs
            WHERE parcel_id = %s
            ORDER BY created_at DESC
            LIMIT 1;
            """,
            (parcel_id,)
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="parcel_id not found")

        run_id, pid, ndvi_t0, ndvi_t1, var_pct, score, created_at = row

        return {
            "parcel_id": pid,
            "latest_run_id": run_id,
            "ndvi_t0": ndvi_t0,
            "ndvi_t1": ndvi_t1,
            "variation_pct": var_pct,
            "risk_score": score,
            "created_at": created_at.isoformat(),
        }
    except Exception as e:
        # Catch unexpected DB errors (e.g. connection refused)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/risk/{parcel_id}/history")
def risk_history(parcel_id: str, limit: int = 10):
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT run_id, parcel_id, ndvi_t0, ndvi_t1, variation_pct, risk_score, created_at, t1_start
            FROM geo.parcel_runs
            WHERE parcel_id = %s
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (parcel_id, limit)
        )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        history = []
        for row in rows:
            run_id, pid, ndvi_t0, ndvi_t1, var_pct, score, created_at, t1_start = row
            history.append({
                "run_id": run_id,
                "ndvi_t0": ndvi_t0,
                "ndvi_t1": ndvi_t1,
                "variation_pct": var_pct,
                "risk_score": score,
                "created_at": created_at.isoformat(),
                "date": t1_start.isoformat() # Useful for frontend timeline
            })

        return history

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
