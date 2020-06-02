# pro-tools-session-info
Read Session Info as Text files exported from Avid Pro Tools

## About
A simple Python 3 module for reading text files exported from [Avid Pro Tools](https://www.avid.com/pro-tools) with various session data. These files a basicalys several CSV sections with metadata, so it's hard to import them directly into table management apps like Excel or Numbers. This module reads every section of `.txt` file into [pandas](https://pandas.pydata.org/) DataFrame object, wich provides fast and handy interface to read, edit and export table-like data. Session and track parameters are also available as attributes. 

## Installation
Installing from PyPi:
```
pip install pro-tools-session-info
```

### Dependencies
* [pandas](https://pandas.pydata.org/)
* [timecode](https://github.com/eoyilmaz/timecode)

Install timecode manually from github to get the latest available version, as the one from PyPi was not updated:
```
pip install git+https://github.com/eoyilmaz/timecode
```

## Usage
### Export session info file
Open session in Pro Tools and use `File -> Export -> Session Info as Text` menu item.
Choose data to export. Specify Timecode in Time Format dropdown to use timecode operations (adding, substracting) for tracks.

### Read info in Python
Read session info from exported `.txt` file:
```
>>> from session import Session, Track
>>> session = Session('sample_files/sample_session_timecode.txt', parse_timecode=True)
>>> print(session)
session_name: sample_session
sample_rate: 48000.000000
bit_depth: 24-bit
session_start_timecode: 00:00:00:00
timecode_format: 24 Frame
#_of_audio_tracks: 3
#_of_audio_clips: 7
#_of_audio_files: 7
framerate: 24
track: A 1, 2 clips
track: A 2, 5 clips
track: A 3, 7 clips
section: online_files_in_session, 7 items
section: offline_files_in_session, 0 items
section: online_clips_in_session, 7 items
section: plugins_listing, 2 items
section: markers_listing, 6 items
```

Tracks are accessible by their name:
```
>>> session.track['A 2'].data
   channel  event                       clip_name   start_time     end_time     duration    timestamp    state
0        1      1  A 2_01                          00:00:23:23  00:00:24:19  00:00:00:20  00:00:23:23  Unmuted
1        1      2  A 2_02                          00:00:25:09  00:00:27:01  00:00:01:16  00:00:25:09  Unmuted
2        1      3  A 2_03                          00:00:28:03  00:00:29:10  00:00:01:07  00:00:28:03  Unmuted
3        1      4  A 2_03                          00:00:32:01  00:00:33:08  00:00:01:07  00:00:28:03  Unmuted
4        1      5  A 2_03                          00:00:36:10  00:00:37:17  00:00:01:07  00:00:28:03  Unmuted

```

Every section and track stores their data as pandas DataFrame, wich supports export to csv:

```
>>> session.section['markers_listing'].to_csv('markers.csv')
```
### Creating changelist with guide track
When session needs to be reconformed manually, it's good to create a changelist in EDL format to automate this task.
1. Create a new mono track with name `RECONFORM GT`
2. Consolidate an empty clip for the whole length of the old cut, that should be reconformed. If you use waveform for manual reconform, consolidate the clip containing reference audio for the old cut.
3. Cut the consolidated clip and conform it to the new cut. Use different start hour for the new cut, so the timecodes for the new and old cuts are not intersected.
4. Export Session Info as Text for the `RECONFORM GT` track. Be sure to include `User Timestamp` while exporting, and don't export subframes.
5. Read exported file in python: `session = Session('reconform.txt', parse_timecode=True)`
6. Export changelist as edl file: `session.track['RECONFORM GT'].to_edl('reconform.edl')`
7. Use exported edl as changelist for the [Conformalizer](http://thecargocult.nz/conformalizer.shtml) or other reconforming app.

## Contact
Copyright 2020, Ilya Putilin.

Please report any bugs to the [GitHub](https://github.com/fantopop/pro-tools-session-info) page.
