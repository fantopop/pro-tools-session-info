import re
from io import StringIO
from os.path import exists, abspath, join
import pandas as pd
from timecode import Timecode


__version__ = '0.1'


##### UTILITIES #####
def normalize(string):
    '''
    Normalize string to use it as python variable name
    * Strip whitespaces
    * Replace spaces with underscores
    * Remove dashes
    * Convert to lowercase
    
    PARAMETERS
    ----------
    string : str
    
    RETURNS
    -------
    normalized : str
    
    '''
    normalized = string.strip()
    normalized = normalized.replace(' ', '_')
    normalized = normalized.replace('-', '')
    normalized = normalized.lower()
    return normalized


def extend_dict(source, target):
    '''
    Add all (key, value) pairs from source dict to target dict.
    '''
    assert type(source) is dict, f'Source dict expected, got: {type(source)}'
    assert type(target) is dict, f'Source dict expected, got: {type(source)}'
    for key, value in source.items():
            target[key] = value

            
def get_parameters(string, target_dict=None):
    '''
    Get parameters from text lines of form:
    PARAMETER NAME:     VALUE
    
    Parameters
    ----------
    lines : input string with lines, one parameter on the line.
    dict_object : add key / value pairs to existing dictionary.
    
    Returns
    -------
    param_dict : dict object with parsed parameter name / value pairs.
    
    '''
    
    # Create new dictionary
    param_dict = dict()
    
    pattern = r'^(.+):\s+(.*)$'
    # Iterate over every line in input string
    for line in string.splitlines():
        match = re.search(pattern, line)
        if match:
            # Delete whitespaces and convert to lower case
            parameter = normalize(match.group(1))
            # Add to dictionary
            param_dict[parameter] = match.group(2)
    
    # Add parsed parameters to specified dictionary if needed
    if target_dict is not None:
        extend_dict(param_dict, target_dict)
    
    return param_dict


def parse_section(section):
    '''
    Parse sections of txt file, exported from Pro Tools.
    
    Session Info as Text file is consisted of several sections, divided by double new lines.
    Exported sections are configured in export window.
    
    PARAMETERS
    ----------
    section : str
    
    RETURNS
    -------
    section_type : str, type of the parsed section: 'header', 'track' or 'section'
    section_name : str, section or track name
    data : dict, DataFrame or Track, parsed data as pandas DataFrame or Track instance, with infered header.
    
    '''
    
    # Parse section parameters, if any present
    parameters = get_parameters(section)
    # Split section into lines
    lines = section.splitlines()
    first_line = normalize(lines[0].replace('  ', '_').replace(' ', ''))
    
    # Define section type
    if 'session_name' in parameters.keys():
        section_type = 'header'
        section_name = 'header'
        data = parameters
    elif 'track_name' in parameters.keys():
        section_type = 'track'
        section_name = parameters['track_name']
        # Skip track_listing line if present in section
        shift = (first_line == 'track_listing')
        data = '\n'.join(lines[shift:])
    else:
        section_type = 'section'
        # Get section name from the first line
        section_name = normalize(first_line)
        # Parse data from other lines into DataFrame
        data = pd.read_csv(StringIO('\n'.join(lines[1:])), sep='\t')
        # Strip whitespaces in column names and convert to lowercase
        data.columns = [normalize(col) for col in data.columns]
        # Strip whitespaces in data
        for column in data.columns:
            if data[column].dtype == 'O':
                data[column] = data[column].str.strip()
    
    return section_type, section_name, data


##### CLASSES #####
class Track:
    '''
    A class to store track EDL and parameters exported from Avid Pro Tools.
    
    INITIALIZATION
    --------------
    Use command File -> Export -> Session Info as Text.
    
    Read all lines for the track from TRACK NAME: to the last event line
    to str variable and initialize new Track() object:
        track = Track(track_section) 
        
    Track parameters are parsed automatically.
    Use parse_timecode and framerate parameters, if the txt file was
    exported in Timecode format.
    
    USAGE
    -----
    Use track.data to get track EDL in pandas DataFrame format.
    All columns with timecodes may be parsed to Timecode() objects.
    If so, vectorized arithmetic operations are supported, e.g.:
    
        track['start_time'] + track['duration'].apply(lambda tc: tc.frame_number)
        
    returns correct vector with timecode values.
    
    '''
    
    def __init__(self, section, parse_timecode=False, framerate=None):
        self.framerate = framerate
        self.timecode_columns = False

        # Read track parameters
        track_parameters = get_parameters(section)
        
        # Add parameters as instance attributes
        extend_dict(track_parameters, self.__dict__)
        
        # Split section text into lines
        lines = section.strip().splitlines()
        
        # Skip first lines with track parameters
        shift = len(track_parameters.keys())
        
        # Read CSV to DataFrame
        df = pd.read_csv(StringIO('\n'.join(lines[shift:])), sep='\t')
        
        # Strip whitespaces in column names and convert to lowercase
        df.columns = [normalize(col) for col in df.columns]
        
        # Strip whitespaces in data
        for column in df.columns:
            if df[column].dtype == 'O':
                df[column] = df[column].str.strip()
                
        self.data = df
        
        if parse_timecode:
            # Add columns with timecodes as series of Timecode objects
            self.parse_timecode(framerate)
        
        # Convert plugins line into list
        if 'plugins' in track_parameters.keys():
            self.plugins = self.plugins.split('\t')
    
    def parse_timecode(self, framerate):
        '''
        Convert strings to Timecode objects
        
        PARAMETERS
        ----------
        framerate : str or int
        
        '''
        assert framerate is not None, 'Specify framerate value to apply'
        for column in self.data.columns[3:-1]:
            parser = lambda tc: Timecode(framerate, tc)
            self.data[column] = self.data[column].apply(parser)
        self.framerate = framerate
        self.timecode_columns = True
    
    def __str__(self):
        # Create new dict with all session parameters except sections dict
        parameters = self.__dict__.copy()
        del parameters['data']
        
        # Add all parameters to output
        lines = [f'{key}: {value}' for key, value in parameters.items()]
        
        # Add clip count
        lines.append(f'{len(self.data)} clips')
            
        return '\n'.join(lines)
    
    def to_edl(self, filepath=None):
        '''
        Export track data to EDL file.
        Track must contain timestamp column and initialized with timecode values.
        To get timestamps export from Pro Tools with Include User Timestamp checked.
        
        PARAMETERS
        ----------
        
        filepath : str or None, path to edl file to write. 
            If None, self.track_name is used as edl filename.
            If filepath already exists export is aborted.
            
        '''
        # Check that timecodes are parsed
        msg = 'Export to EDL is supported only for tracks with parsed timecode values'
        assert self.timecode_columns, msg
        
        # Check if TIMESTAMP column is exported from Pro Tools
        msg = 'Can\'t find source timecode. Try exporting from Pro Tools with Include User Timestamp checkmark'
        assert 'timestamp' in self.data.columns, msg
        
        # Define output filename if not specified
        if filepath is None:
            filepath = self.track_name + '.edl'
        # Check that output file not exists
        assert not exists(filepath), f'File {abspath(filepath)} already exists'
        
        # Pad event number with zeroes
        pad = max(3, len(str(self.data['event'].max())))
        
        # Create new DataFrame for output EDL
        df = pd.DataFrame(self.data['event'].apply(lambda x: str(x).rjust(pad, '0')))
        
        # Add data columns for the edl
        df['reel'] = self.data['clip_name']
        df['track'] = 'A'
        df['event_type'] = 'C'
        df['src_start_tc'] = self.data['timestamp']
        duration_frame_number = self.data['duration'].apply(lambda tc: tc.frame_number)
        df['src_end_tc'] = self.data['timestamp'] + duration_frame_number
        df['rec_start_tc'] = self.data['start_time']
        df['rec_end_tc'] = self.data['end_time']
        
        output = []
        # Add TITLE to EDL header
        output.append(f'TITLE:\t{self.track_name}')
        # Add FCM to EDL header
        if str(self.framerate) in ['29.97', '59.94']:
            fcm = 'DROP FRAME'
        else:
            fcm = 'NON-DROP FRAME'
        output.append(f'FCM:\t{fcm}')
        output.append('\n')
    
        # Export tracks events to CSV string buffer
        string_io = StringIO()
        df.to_csv(string_io, sep='\t', header=False, index=False)
        output.append(string_io.getvalue())
    
        # Write to file
        with open(filepath, 'w') as f:
            f.write('\n'.join(output))
            

class Session:
    '''
    A class to store data parsed from txt file with Avid Pro Tools session info data.
    
    INITIALIZATION
    --------------
    Use command File -> Export -> Session Info as Text.
    
    Read exported txt file:
        session = Session('path/to/session_info.txt')
    
    Session parameters are parsed automatically, including session framerate.
    
    USAGE
    -----
    Session data is available as pandas DataFrames.
    Use session.sections to get list of parsed data sections.
    Every track is stored in Session.track attribute as Track() object.
    Use session.tracks to get list of parsed tracks.
    Track EDL is available as pandas DataFrame object.
    '''
    
    def __init__(self, filepath, parse_timecode=True):
        '''
        Read session info txt file, exported from Pro Tools.
        
        PARAMETERS
        ----------
        filepath : str, path to txt file
        parse_timecode : bool
            apply only if Timecode is used as Time Format while exporting from Pro Tools.
            Framerate is read from session info header.
        '''
        # Read the whole file
        with open(filepath, 'r') as f:
            source_text = f.read()
        
        # Strip all newlines at end or tail
        source_text = source_text.strip()
        # Split into sections, divided by triple newlines.
        source_sections = source_text.split(sep='\n\n\n')
        
        # Create dictionary for sections and tracks
        self.section = dict()
        self.track = dict()
        
        # Parse sections
        for section in source_sections:
            section_type, section_name, data = parse_section(section)
            if section_type == 'header':
                # Copy header data as instance attributes
                extend_dict(data, self.__dict__)
                # Add framerate value
                if 'timecode_format' in data.keys():
                    self.framerate = self.timecode_format.split()[0]
                else:
                    self.framerate = None
            elif section_type == 'track':
                self.track[section_name] = Track(data, parse_timecode, self.framerate)
            else:
                self.section[section_name] = data    
        
    @property
    def sections(self):
        '''
        Returns list of all parsed sections
        '''
        return list(self.section.keys())
    
    @property
    def tracks(self):
        '''
        Returns session track names
        '''
        return list(self.track.keys())
    
    def __str__(self):
        # Create new dict with all session parameters except sections dict
        parameters = self.__dict__.copy()
        del parameters['section']
        del parameters['track']
        
        # Add all parameters to output
        lines = [f'{key}: {value}' for key, value in parameters.items()]
        
        # Add track names to output
        for track_name in self.tracks:
            lines.append(f'track: {track_name}, {len(self.track[track_name].data)} clips')
        
        # Add section names to output
        for section_name in self.sections:
            lines.append(f'section: {section_name}, {len(self.section[section_name])} items')
            
        return '\n'.join(lines)