from typing import Optional
from pydantic import BaseModel


class SleepPhases(BaseModel):
    deep_minutes: Optional[int] = None
    light_minutes: Optional[int] = None
    rem_minutes: Optional[int] = None
    awake_minutes: Optional[int] = None


class SleepRecord(BaseModel):
    date: str
    total_duration_minutes: Optional[int] = None
    phases: Optional[SleepPhases] = None
    sleep_start: Optional[str] = None  # ISO time string, e.g. "22:30"
    sleep_end: Optional[str] = None    # ISO time string, e.g. "06:45"
    quality_score: Optional[int] = None  # 0-100 if provided by API


class HRVRecord(BaseModel):
    date: str
    rmssd_avg: Optional[float] = None    # Nacht-Durchschnitt RMSSD (ms)
    hrv_index: Optional[int] = None      # Coros HRV Index 0-100
    rmssd_min: Optional[float] = None
    rmssd_max: Optional[float] = None


class StoredAuth(BaseModel):
    access_token: str
    user_id: str
    region: str
    timestamp: int  # Unix milliseconds
