#!/usr/bin/env python3
import os
import glob
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import gpxpy
from lxml import etree
import math

def parse_args():
    p = argparse.ArgumentParser(
        description="Combine Apple Health XML + GPX into a TCX for Strava"
    )
    p.add_argument("--xml-dir", required=True,
                   help="Directory containing your Health XML export files")
    p.add_argument("--gpx", required=True, help="GPX route file")
    p.add_argument("--output", default="workout.tcx",
                   help="Output TCX filename")
    return p.parse_args()

def parse_health_xml(xml_dir):
    records = []
    workouts = []
    for fn in glob.glob(os.path.join(xml_dir, "*.xml")):
        tree = ET.parse(fn)
        root = tree.getroot()
        # Workout entries
        for w in root.findall("Workout"):
            sd = datetime.fromisoformat(w.get("startDate").replace("Z","+00:00"))
            ed = datetime.fromisoformat(w.get("endDate").replace("Z","+00:00"))
            workouts.append({
                "start": sd,
                "end": ed,
                "type": w.get("workoutActivityType"),
                "distance": float(w.get("totalDistance",0)),
                "calories": float(w.get("totalEnergyBurned",0)),
                "metadata": w.attrib
            })
        # Heart rate records
        for r in root.findall("Record[@type='HKQuantityTypeIdentifierHeartRate']"):
            t = datetime.fromisoformat(r.get("startDate").replace("Z","+00:00"))
            hr = float(r.get("value"))
            records.append(("hr", t, hr))
        # (you could add steps/calories similarly)
    return workouts, records

def find_matching_workout(workouts, gpx_start):
    for w in workouts:
        if w["start"] <= gpx_start <= w["end"]:
            return w
    return None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dlambda = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def build_tcx(workout, hr_records, gpx_file, out_file):
    # Parse GPX
    with open(gpx_file) as f:
        gpx = gpxpy.parse(f)
    trk = gpx.tracks[0].segments[0].points
    # Compute cumulative distance
    cum = 0.0
    pts = []
    prev = None
    for p in trk:
        if prev:
            cum += haversine(prev.latitude, prev.longitude,
                             p.latitude, p.longitude)
        pts.append((p.time.replace(tzinfo=timezone.utc),
                    p.latitude, p.longitude,
                    p.elevation or 0.0, cum))
        prev = p

    # Filter HR between workout window
    hrs = [(t, v) for (_typ, t, v) in hr_records
           if workout["start"] <= t <= workout["end"]]

    NS = {
        None: "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }
    tcx = etree.Element("TrainingCenterDatabase", nsmap=NS)
    act = etree.SubElement(
        etree.SubElement(tcx, "Activities"),
        "Activity", Sport="Other"
    )
    etree.SubElement(act, "Id").text = workout["start"].isoformat()
    lap = etree.SubElement(
        act, "Lap", StartTime=workout["start"].isoformat()
    )
    etree.SubElement(lap, "TotalTimeSeconds").text = str((workout["end"]-workout["start"]).total_seconds())
    etree.SubElement(lap, "DistanceMeters").text = str(workout["distance"])
    etree.SubElement(lap, "Calories").text = str(int(workout["calories"]))
    etree.SubElement(lap, "Intensity").text = "Active"
    etree.SubElement(lap, "TriggerMethod").text = "Manual"
    track = etree.SubElement(lap, "Track")

    # merge trackpoints with nearest HR by timestamp
    hr_idx = 0
    for time, lat, lon, ele, dist in pts:
        tp = etree.SubElement(track, "Trackpoint")
        etree.SubElement(tp, "Time").text = time.isoformat()
        pos = etree.SubElement(tp, "Position")
        etree.SubElement(pos, "LatitudeDegrees").text = str(lat)
        etree.SubElement(pos, "LongitudeDegrees").text = str(lon)
        etree.SubElement(tp, "AltitudeMeters").text = str(ele)
        etree.SubElement(tp, "DistanceMeters").text = str(dist)
        # heart rate if available
        while hr_idx+1 < len(hrs) and hrs[hr_idx+1][0] <= time:
            hr_idx += 1
        if hr_idx < len(hrs) and abs((hrs[hr_idx][0]-time).total_seconds()) < 5:
            hr_elem = etree.SubElement(tp, "HeartRateBpm")
            etree.SubElement(hr_elem, "Value").text = str(int(hrs[hr_idx][1]))

    # write file
    tree = etree.ElementTree(tcx)
    tree.write(out_file, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    print(f"✓ Written TCX: {out_file}")

def main():
    args = parse_args()
    workouts, records = parse_health_xml(args.xml_dir)
    # get GPX start time
    with open(args.gpx) as f:
        gpx = gpxpy.parse(f)
    start = gpx.tracks[0].segments[0].points[0].time.replace(tzinfo=timezone.utc)

    w = find_matching_workout(workouts, start)
    if not w:
        raise RuntimeError("No workout found matching GPX start time.")
    build_tcx(w, records, args.gpx, args.output)

if __name__ == "__main__":
    main()
