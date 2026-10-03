# SHADOW — software gates pending

Read-only EPS_CAPACITY_DATASET.csv and STEERING_RETURN_EVENT +/-10 second windows.
No changes to steering or longitudinal tuning. Unknown lateral-error input is blank.
Files default to /data/media/0/mycrv_v33; nonblocking bounded logger, 64 MiB CSV rotation,
20 event windows retained. Dropped samples are counted. A route ending before +10 s
does not create a falsely complete event. CLOSED_COURSE_REQUIRED for physical evidence.
