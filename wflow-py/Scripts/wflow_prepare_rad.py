# -*- coding: utf-8 -*-
"""
Created on Tue Nov 25 08:22:48 2014

@author: schelle
"""

# test radiation


from pcraster import *

setglobaloption("degrees")

def lattometres(lat):
    """"
    Determines the length of one degree lat/long at a given latitude (in meter).
    Code taken from http:www.nga.mil/MSISiteContent/StaticFiles/Calculators/degree.html
    Input: map with lattitude values for each cell
    Returns: length of a cell lat, length of a cell long
    """
    #radlat = spatial(lat * ((2.0 * math.pi)/360.0))
    #radlat = lat * (2.0 * math.pi)/360.0
    radlat = spatial(lat) # pcraster cos/sin work in degrees!
    
    
    m1 = 111132.92        # latitude calculation term 1
    m2 = -559.82        # latitude calculation term 2
    m3 = 1.175            # latitude calculation term 3
    m4 = -0.0023        # latitude calculation term 4
    p1 = 111412.84        # longitude calculation term 1
    p2 = -93.5            # longitude calculation term 2
    p3 = 0.118            # longitude calculation term 3
    # # Calculate the length of a degree of latitude and longitude in meters
    
    latlen = m1 + (m2 * cos(2.0 * radlat)) + (m3 * cos(4.0 * radlat)) + (m4 * cos(6.0 * radlat))
    longlen = (p1 * cos(radlat)) + (p2 * cos(3.0 * radlat)) + (p3 * cos(5.0 * radlat))
        
    return latlen, longlen  
    
def detRealCellLength(ZeroMap,sizeinmetres):
    """
    Determine cellength. Always returns the length
    in meters.
    """
    
    if sizeinmetres:
            reallength = celllength()
            xl = celllength()
            yl = celllength()
    else:
        aa = ycoordinate(boolean(cover(ZeroMap + 1,1)))
        yl, xl = lattometres(aa)
           
        xl = xl * celllength()
        yl = yl * celllength()
        # Average length for surface area calculations. 
        
        reallength = (xl + yl) * 0.5
        
    return xl,yl,reallength



def correctrad(Day,Hour,Lat,Lon,Slope,Aspect,Altitude,Altitude_UnitLatLon):
    """ 
    Determines radiation over a DEM assuming clear sky for a specified hour of
    a day
    
    :var Day: Day of the year (1-366)
    :var Hour: Hour of the day (0-23)
    :var Lat: map with latitudes for each grid cell
    :var Lon: map with lonitudes for each grid cell
    :var Slope: Slope in degrees
    :var Aspect: Aspect in degrees relative to north for each cell
    :var Altitude: Elevation in metres
    :var Altitude_Degree: Elevation in degrees. If the actual pcraster maps
                          are in lat lon this maps should hold the Altitude converted
                          to degrees. If the maps are in metres this maps should also
                          be in metres

    :return Stot: Total radiation on the dem, shadows not taken into account
    :return StotCor: Total radiation on the dem taking shadows into acount
    :return StotFlat: Total radiation on the dem assuming a flat surface
    :return Shade: Map with shade (0) or no shade (1) pixels
    """
    
    print "Soldec..."
    Sc  = 1367.0          # Solar constant (Gates, 1980) [W/m2]
    Trans   = 0.6             # Transmissivity tau (Gates, 1980)    
    pi = 3.1416
    AtmPcor = pow(((288.0-0.0065*Altitude)/288.0),5.256) 
    #Lat = Lat * pi/180
    ##########################################################################
    # Calculate Solar Angle and correct radiation ############################
    ##########################################################################
    # Solar geometry
    # ----------------------------
    # SolDec  :declination sun per day  between +23 & -23 [deg]
    # HourAng :hour angle [-] of sun during day
    # SolAlt  :solar altitude [deg], height of sun above horizon
    # SolDec  = -23.4*cos(360*(Day+10)/365);
    # Now added a new function that should work on all latitudes! 
    #theta    =(Day-1)*2 * pi/365  # day expressed in radians
    theta    =(Day-1)*360.0/365.0  # day expressed in degrees
     
    SolDec =180/pi *  (0.006918-0.399912 * cos(theta)+0.070257 * sin(theta) -  0.006758 * cos(2*theta)+0.000907 * sin(2*theta) -  0.002697 *           cos(3*theta)+0.001480 * sin(3*theta))
    
    #HourAng = 180/pi * 15*(Hour-12.01)
    HourAng = 15.0*(Hour-12.01) 
    SolAlt  = scalar(asin(scalar(sin(Lat)*sin(SolDec)+cos(Lat)*cos(SolDec)*cos(HourAng))))
    
    # Solar azimuth                    
    # ----------------------------
    # SolAzi  :angle solar beams to N-S axes earth [deg]
    SolAzi = scalar(acos((sin(SolDec)*cos(Lat)-cos(SolDec)* sin(Lat)*cos(HourAng))/cos(SolAlt)))
    SolAzi = ifthenelse(Hour <= 12, SolAzi, 360 - SolAzi)
    
    print "Solazi..."
    # Surface azimuth
    # ----------------------------
    # cosIncident :cosine of angle of incident; angle solar beams to angle surface
    cosIncident = sin(SolAlt)*cos(Slope)+cos(SolAlt)*sin(Slope)*cos(SolAzi-Aspect)
    # Fro flat surface..  
    FlatLine = spatial(scalar(0.00001))
    FlatSpect = spatial(scalar(0.0000))
    cosIncidentFlat = sin(SolAlt)*cos(FlatLine)+cos(SolAlt)*sin(FlatLine)*cos(SolAzi-FlatSpect)
    # Fro flat surface..    
    #cosIncident = sin(SolAlt) + cos(SolAzi-Aspect)

    print "Shading ..."
    # Critical angle sun
    # ----------------------------
    # HoriAng  :tan maximum angle over DEM in direction sun, 0 if neg 
    # CritSun  :tan of maximum angle in direction solar beams
    # Shade    :cell in sun 1, in shade 0
    # NOTE: for a changing DEM in time use following 3 statements and put a #
    #       for the 4th CritSun statement
    HoriAng   = cover(horizontan(Altitude_UnitLatLon,directional(SolAzi)),0)
    #HoriAng   = horizontan(Altitude,directional(SolAzi))
    HoriAng   = ifthenelse(HoriAng < 0, scalar(0), HoriAng)
    CritSun   = ifthenelse(SolAlt > 90, scalar(0), scalar(atan(HoriAng)))
    Shade   = SolAlt > CritSun
    #Shade = spatial(boolean(1))
    # Radiation outer atmosphere
    # ----------------------------
    #report(HoriAng,"hor.map")
    print "Radiation..."
    OpCorr = Trans**((sqrt(1229+(614*sin(SolAlt))**2) -614*sin(SolAlt))*AtmPcor)    # correction for air masses [-] 
    Sout   = Sc*(1+0.034*cos(360*Day/365.0)) # radiation outer atmosphere [W/m2]
    Snor   = Sout*OpCorr                   # rad on surface normal to the beam [W/m2]

    # Radiation at DEM
    # ----------------------------
    # Sdir   :direct sunlight on dem surface [W/m2] if no shade
    # Sdiff  :diffuse light [W/m2] for shade and no shade
    # Stot   :total incomming light Sdir+Sdiff [W/m2] at Hour
    # Radiation :avg of Stot(Hour) and Stot(Hour-HourStep)
    # NOTE: PradM only valid for HourStep & DayStep = 1

    
    SdirCor   = ifthenelse(Snor*cosIncident*scalar(Shade)<0,0.0,Snor*cosIncident*scalar(Shade))
    Sdir   = ifthenelse(Snor*cosIncident<0,0.0,Snor*cosIncident)
    SdirFlat   = ifthenelse(Snor*cosIncidentFlat<0,0.0,Snor*cosIncidentFlat)
    Sdiff  = ifthenelse(Sout*(0.271-0.294*OpCorr)*sin(SolAlt)<0, 0.0, Sout*(0.271-0.294*OpCorr)*sin(SolAlt))
    #AtmosDiffFrac = ifthenelse(Sdir > 0, Sdiff/Sdir, 1)          



    # Stot   = cover(Sdir+Sdiff,windowaverage(Sdir+Sdiff,3));     # Rad [W/m2]
    Stot   = Sdir + Sdiff                                             # Rad [W/m2]
    StotCor   = SdirCor + Sdiff                                   # Rad [W/m2]
    StotFlat = SdirFlat + Sdiff
    
    
     
    return Stot, StotCor, StotFlat, Shade, 


def GenRadMaps(SaveDir,SaveName,Lat,Lon,Slope,Aspect,Altitude,DegreeDem):
    """ 
    Generates daily radiation maps for a whole year.
    It does so by running correctrad for a whole year with hourly
    steps and averaging this per day.
    """

    
    for Day in range(1,365):
        avgrad = 0.0 * Altitude
        _avgrad = 0.0 * Altitude
        _flat = 0.0 * Altitude
        avshade = 0.0 * Altitude
        id = 1
        for Hour in range(4,22):
            print "day: " + str(Day) + " Hour: " + str(Hour)
            cradnodem, crad,  flat, shade = correctrad(Day,Hour,Lat,Lon,Slope,Aspect,Altitude,DegreeDem)           
            avgrad=avgrad + crad
            _flat = _flat + flat
            _avgrad=_avgrad + cradnodem
            avshade=avshade + scalar(shade)
            nrr = "%03d" % id
            #report(crad,"tt000000." + nrr)
            #report(shade,"sh000000." + nrr)
            #report(cradnodem,"ttr00000." + nrr)
            id = id + 1
        
        nr = "%0.3d" % Day
        report(avgrad/24.0,SaveDir + "/" + SaveName + "00000." + nr)
        report(_avgrad/24.0,SaveDir + "/_" + SaveName + "0000." + nr)
        report(avshade/24.0,SaveDir + "/SHADE000." + nr)
        report(_flat/24.0,SaveDir + "/FLAT0000." + nr)
        report(cover(avgrad/_flat,1.0),SaveDir + "/RATI0000." + nr)




print "Load and create slope..."
thedem = "SRTM2_V3_NASA30_blkmean_gtopo_north_SMALL.map"   
#thedem ="demaa.map"
setclone(thedem)
dem = readmap(thedem)

LAT= ycoordinate(boolean(dem))
LON = xcoordinate(boolean(dem))
#LAT = spatial(scalar(53))
#LON= spatial(scalar(10))
Slope = slope(dem)
xl, yl, reallength = detRealCellLength(dem * 0.0, 0)
Slope = max(0.00001, Slope * celllength() / reallength)
#Slope = max(0.00001,slope(dem))
# Convert to degrees
Slope = scalar(atan(Slope))

print "Aspect etc.."
Aspect = cover(scalar(aspect(dem)),0.0)
report(Slope,"slope.map")
report(Aspect,"aspect.map")
#report(reallength,"reallength.map")
degreedem = dem * celllength() / reallength

#report(degreedem,"degreedem.map")
#dem = 300
#crad = correctrad(Day,Hour,LAT,LON,Slope,Aspect,dem)

GenRadMaps("OUTPUT","RAD",LAT,LON,Slope,Aspect,dem,degreedem)
#GenRadMaps("OUTPUT","RAD",LAT,LON,Slope,Aspect,dem,dem)