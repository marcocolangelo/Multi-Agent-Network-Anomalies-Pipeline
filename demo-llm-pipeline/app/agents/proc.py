import io, pandas as pd, numpy as np, ipaddress
from sklearn.preprocessing import RobustScaler
from app.core.messages import Msg
from app.utils.tracing import log
from app.core.bus import EventBus

class NetworkLogPreprocessor:
    def __init__(self):
        self.scaler = RobustScaler()

    def preprocess(self, raw_csv: str):
        df = pd.read_csv(io.StringIO(raw_csv), header=None, names=[
            'timestamp','src_ip','dst_ip','src_port','dst_port','protocol',
            'bytes','packets','duration','cell_id','user_hash'
        ])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        df["hour"] = df["datetime"].dt.hour
        return df

async def proc_listener(bus: EventBus, msg: Msg):
    raw = msg.payload["raw_logs"]
    log("Proc ▶ start")

    pre = NetworkLogPreprocessor()
    csv_part = "\n".join(l for l in raw.splitlines() if l and l[0].isdigit())
    df = pre.preprocess(csv_part)
    log(f"Proc ▶ produced the following DataFrame:\n{df.head().to_string()}")
    await bus.publish(Msg(trace_id=msg.trace_id,
                          role="INGEST_OK",
                          payload={"df": df}))
