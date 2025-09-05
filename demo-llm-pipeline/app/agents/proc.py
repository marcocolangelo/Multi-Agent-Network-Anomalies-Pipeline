import csv
import chromadb
import io, pandas as pd, numpy as np, ipaddress
from sentence_transformers import SentenceTransformer
from sklearn.preprocessing import RobustScaler
from app.core.messages import Msg
from app.utils.tracing import log
from app.core.bus import EventBus
from app.utils.config import settings

class NetworkLogPreprocessor:
    def __init__(self):
        self.scaler = RobustScaler()
        self.POOLDB_PATH = settings.POOL_DB_PATH

    def preprocess(self, raw_csv: str):
        df = pd.read_csv(io.StringIO(raw_csv), header=None, names=[
            'timestamp','src_ip','dst_ip','src_port','dst_port','protocol',
            'bytes','packets','duration','cell_id','user_hash'
        ])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        df["hour"] = df["datetime"].dt.hour
        return df

    def setup_vector_db(self):
        db = chromadb.Client()
        collection = db.create_collection("incident_reports")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        # Indicizza i report storici
        # Indicizza ogni anomalia come nodo, usando il nome come documento e id
        with open(self.POOLDB_PATH, "r") as f:
            reports = []
            current_report = {}
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Anomaly_id"):
                    if current_report:
                        reports.append(current_report)
                        current_report = {}
                    parts = line.split(",", 1)
                    current_report["Anomaly_id"] = parts[1].strip() if len(parts) > 1 else ""
                elif line.startswith("Anomaly_description"):
                    parts = line.split(",", 1)
                    current_report["Anomaly_description"] = parts[1].strip() if len(parts) > 1 else ""
                else:
                    # Assume the rest is the report content
                    current_report.setdefault("Report", []).append(line)
            if current_report:
                reports.append(current_report)

            for i, report in enumerate(reports):
                r = "\n".join(report["Report"])
                anomaly_id = report.get("Anomaly_id", "")
                anomaly_description = report.get("Anomaly_description", "")
                if anomaly_id:
                    embedding = model.encode(anomaly_description).tolist()
                    collection.add(
                        documents=[anomaly_description],
                        embeddings=[embedding],
                        ids=[str(i)],
                        metadatas=[{"full_report": r, "description": anomaly_description}]
                    )

        return collection, model

async def proc_listener(bus: EventBus, msg: Msg):
    from app.utils.tracing import log_gui
    raw = msg.payload["raw_logs"]
    log_gui("Proc", "start")

    pre = NetworkLogPreprocessor()
    csv_part = "\n".join(l for l in raw.splitlines() if l and l[0].isdigit())
    df = pre.preprocess(csv_part)
    log_gui("Proc", f"produced the following DataFrame:\n{df.head().to_string()}")
    collection, model = pre.setup_vector_db()
    log_gui("Proc", f"produced the following vector DB:\n{collection}\n{model}")
    await bus.publish(Msg(trace_id=msg.trace_id,
                          role="INGEST_OK",
                          payload={"df": df, "collection": collection, "model": model}))
