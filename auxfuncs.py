import os
from datetime import datetime, timedelta
import configparser
import shapely.geometry
import auxfuncs as aux
from loguru import logger

## configuration for this machine, should be customized for each machine
##
def getConfig():
    params = {}
    config = configparser.ConfigParser()
    config.read('configuration.ini', encoding='utf-8')
    params['workdir'] = config['WORKING']['workpath']
    params['binpath'] = config['WORKING']['binpath']
    params['db_file'] = config['WORKING']['dbfname']
    params['exe_decart'] = os.path.join(config['WORKING']['binpath'], f'decart{config["DECART"]["version"]}', 'decart.exe')
    params['exe_rasar']  = os.path.join(config['WORKING']['binpath'], f'decart{config["DECART"]["version"]}', 'convert', 'rasar.exe')
    params['exe_vips']   = os.path.join(config['WORKING']['binpath'], f'decart{config["DECART"]["version"]}', 'convert', 'vips.exe')
    params['tempzone']   = config['WORKING']['tempzone']
    params['decart_ver'] = config["DECART"]["version"]
    return params

def getConfigHWcomponents():
    config = configparser.ConfigParser()
    config.read('configuraion.ini', encoding='utf-8')
    envOS = config['ENVIRONMENT']['os']
    envCPU = config['ENVIRONMENT']['cpu']
    envGPU = config['ENVIRONMENT']['gpu']
    envRAM = config['ENVIRONMENT']['ram']
    return envOS, envCPU, envGPU, envRAM

## Returns the current time in the format yyyy-mm-dd HH:MM:SS.
## 
def sNOW():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def timestampDelta2String(tsdelta):
    #tsstr = (datetime.min+timedelta(seconds=tsdelta)).strftime('%H:%M:%S')[:-3]
    tsstr = (datetime.min+timedelta(seconds=tsdelta)).strftime('%H:%M:%S')
    return tsstr

def printmsg(logstr, uilog=False):
    print(f'[{sNOW()}]{logstr}')
    if uilog:
        if ('INFO' in logstr) or ('LOG' in logstr):
            logger.info(logstr)
        elif 'WARNING' in logstr:
            logger.warning(logstr)
        elif 'ERROR' in logstr:
            logger.error(logstr)
        else:
            logger.debug(logstr)

def printdata(logstr):
    print(f'{logstr}')
    logger.info(logstr)

## replace ' ' with '_' in the filename
def replaceSpace2underscore(fname):
    thisfile = fname
    if ' ' in fname:
        mpath, mfile = os.path.split(fname)
        tmpfile = mfile.replace(' ', '_')
        thisfile = os.path.join(mpath, tmpfile)
        os.rename(fname, thisfile)
    return thisfile

def getCellTilePos(segments):
    leftx, lefty, rightx, righty = 100000000, 100000000, 0, 0
    for i, xy in enumerate(segments):
        x, y = xy
        if x < leftx:
            leftx = x
        if x > rightx:
            rightx = x
        if y < lefty:
            lefty = y
        if y > righty:
            righty = y
    tilex = leftx-20 if leftx > 20 else 0
    tiley = lefty-20 if lefty > 20 else 0
    tilew = rightx - leftx + 40
    tileh = righty - lefty + 40
    return tilex, tiley, tilew, tileh

def calculateCellArea(segments, mpp=0.25):
    convex = []
    for i, xy in enumerate(segments):
        x, y = xy
        convex.append((x*mpp, y*mpp))
    thiscell = shapely.geometry.Polygon(convex)
    return thiscell.area

def getIntersectionArea(x1, y1, w1, h1, x2, y2, w2, h2):
    # Find intersection coordinates
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    # Check if there is an intersection
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0, 0  # No intersection
    
    # Calculate intersection area
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    # calculate overlap ratio
    area1 = w1 * h1
    area2 = w2 * h2
    overlap_ratio = intersection_area / min(area1, area2)
    
    return overlap_ratio, intersection_area

