This script dynamically merges Apple Health XML records with GPX route files into a single, Strava-compatible TCX file. It aligns asynchronous heart rate data with GPS coordinates and calculates cumulative distance via the Haversine formula.

---

### The Motive 🏔️🏔️🏔️

I wanted to upload some old Norway hiking trips and my first-ever marathon from 2023 to Strava, but my data was siloed: I had the GPX route and the XML health exports from an old Apple Watch I no longer own. Since Strava requires TCX for a smooth upload with heart rate, and I couldn't find a simple, free tool to bridge the two, I built this pipeline. It worked perfectly to fix my problem, and can be used for any workout data!

---

### How to use it:

### 1. Setup
```
pip install -r requirements.txt
```

### 2. Convert your data
```
python generate_tcx.py --xml-dir ./health_data --gpx ./trip.gpx --output hike.tcx
```

where:

***--xml-dir***: Folder containing your Apple Health XML exports.

***--gpx***: Path to your specific GPX route file.

***--output***: Final filename for Strava upload.

_Happy training!_


<p align="center">
  <img src="HikePic.jpg" width="600px">
</p>