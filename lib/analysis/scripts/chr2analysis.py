__author__ = 'pbmanis'

from collections import OrderedDict
import re
import numpy as np
import scipy.stats

initialized = False

if not initialized:
    global summary, initialized
    summary=[]
    initialized = True


class Params(object):
    """
    Class to make organized data a bit like a C struct.
    Instantiate by calling:
    p = Params(mode='tail', chfit=True, exp0fit=False, t0 = 3.59, wx={'one': 1, 'C': [1,2,3,4]) (etc)
    then p.mode returns 'tail', etc.
    p.list() provides a nice print out of the variable.
    """
    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def list(self):
        o = dir(object())
        for x in dir(self):
            if x in o:
                continue
            if x[0:2] == '__':
                continue
            if x == 'list':
                continue
            print '   ' + x + ' = ',
            print eval('self.' + x)

def protocolInfo(fh, inputs, derivative):
    """
    protocolInfo is called through "Process" for every directory (epoch run) stored below the protocol directory.
    fh is the file handle for the current file we are processing
    inputs is the result of the analysis, which is the result of the threshold detection of spikes
    inputs contains information about the spike latency, width, peak, etc.
    The routine returns the "result", which is an ordered dictionary, for each call.
    However, it also updates the global list "summary", thus concatenating the results into a single
    array.
    """
    global summary
    nspikes = len(inputs)
    #print inputs
    reps = fh.parent().info()['protocol']['conf']['repetitions'] # fh.info()[('protocol', 'repetitions')]
    pulseDurIndex = fh.info()[('LED-Blue', 'Command.PulseTrain_length')]

    fn = fh.shortName()
    # find date string in the path, and return path to current data set
    # allows us to identify the data set by date, slice, cell, protocol, etc.
    dm = re.compile(r'(\d{4,4})\.(\d{2,2})\.(\d{2,2})*')
    dsearch = dm.search(fh.name())
    expname = fh.name()[dsearch.start():] # pull full path for experiment here, but leave out everything above the date
    pulseDur = fh.parent().info()['sequenceParams'][('LED-Blue','Command.PulseTrain_length')][pulseDurIndex]
    pulseTrainInfo = fh.parent().info()['devices']['LED-Blue']['channels']['Command']['waveGeneratorWidget']['stimuli']['PulseTrain']
    startTime = pulseTrainInfo['start']['value'] # retrieve start time
    rep = fh.info()[('protocol', 'repetitions')]
    ipi = pulseTrainInfo['interpulse_length']['value'] # retrieve interpulse interval
    npulses = pulseTrainInfo['pulse_number']['value'] # retrieve number of pulses in train
    spikeTimes = [t['time'] for t in inputs]
    # figure max of derivative of the data after each stimulus pulse. 5 msec window.
    t=derivative.xvals("Time")
    slopes = np.zeros(npulses)
    for n in range(npulses):
        t0 = startTime + n * ipi
        t1 = t0 + 3e-3
        x = np.where((t > t0) & (t <= t1))
        slopes[n] = np.max(derivative[x])


    res = OrderedDict([('Experiment: ', expname), ('File: ', fn), ('startTime', startTime),
                       ('NPulses', npulses), ('IPI', ipi), ('PulseDur', pulseDur), ('Reps', reps), ('thisRep', rep),
                       ('NSpikes', nspikes), ('SpikeTimes', spikeTimes), ('Slopes', slopes)])
    summary.append(res)
    return res

def getSummary():
    global summary
    return summary

def clearSummary():
    global summary
    summary = []

def printSummary(plotWidget = None):
    global summary
    if len(summary) == 0:
        return
    title = ''
    kl = []
    excludeKeys =  ['Experiment: ', 'SpikeTimes', 'Reps']
    print '----------------------------------'
    if excludeKeys[0] in summary[0].keys():
        print 'Experiment: %s  reps: %d' % (summary[0][excludeKeys[0]], summary[0]['Reps'])
    for s in summary[0].keys():
        if s in excludeKeys:
            continue
        title = title + s + '\t'
        kl.append(s)
    print title
    for i in range(len(summary)):
        for k in kl: # keeps order
            if k in excludeKeys:
                continue
            print summary[i][k], '\t',
        print ''
    print '----------------------------------'
    print '\n'
    # generate a summary that ranks data by pulse duration
    # analysis:
    # mean # spikes per stimulus (count spikes from stimulus onset to the ipi following
    # mean latency of spikes vs stimulus number
    # mean std of spikes vs stimulus number
    # assumption: what varies is the pulse Duration, so we create a dictionary to organize the values
    # and sequence over that.
    pdurs = [x['PulseDur'] for x in summary]
    npulses = [x['NPulses'] for x in summary]
    reps = summary[0]['Reps'] # wont change in protocol
    uniqDurs, uniqDursIndx = np.unique(pdurs, return_inverse=True)
    ndur = len(uniqDurs)
    npul = npulses[0] # assumption - the same number of pulses in each run
    nspk = np.zeros((ndur, npul, reps))
    lat = np.zeros((ndur, npul, reps))
    durs = np.zeros((ndur, npul, reps))
    slopes = np.zeros((ndur, npul, reps))
    rep = [[0]*npul] * ndur
    for du in range(len(summary)):
        s = summary[du] # get summary for this duration
        duration = s['PulseDur']
        st = np.array(s['SpikeTimes'])
        # now loop through and fill the arrays to make calculations
        repc = s['thisRep']
        for n in range(s['NPulses']):
            t0 = s['startTime'] + n * s['IPI'] # start time for this pulse window
            t1 = t0 + s['IPI'] # end time for this pulse window
            x = np.intersect1d(np.where(st > t0)[0].tolist(), np.where(st <= t1)[0].tolist())
            if len(x) > 0:
                lat[uniqDursIndx[du], n, repc] = st[x[0]]-t0
            else:
                lat[uniqDursIndx[du], n, repc] = np.nan
            durs[uniqDursIndx[du], n, repc] = duration # save the associated pulse duration
            nspk[uniqDursIndx[du], n, repc] = len(x)
            rep[uniqDursIndx[du]][n] = repc
            slopes[uniqDursIndx[du], n, repc] = s['Slopes'][n]

    meanlat = scipy.stats.nanmean(lat, axis=2)
    meannspk = scipy.stats.nanmean(nspk, axis=2)
    stdlat = scipy.stats.nanstd(lat, axis = 2)
    meanslope = scipy.stats.nanmean(slopes, axis=2)
    #print meanlat[0]
    #print stdlat[0]
    #print meannspk[0]
    #print meanslope[0]
    #print durs[:,:,0]

    xmax = 0.
    for i, plw in enumerate(plotWidget):
        plw.plotItem.clear()
#        plotWidget.plotItem.scatterPlot().clear()
        if i == 0:
            if npul > 2:
                plw.plotItem.scatterPlot().setData(x=np.arange(npul), y=meanslope[0], symbol='o')
                plw.plotItem.setLabel('left', 'Slope (V/s)')
                plw.plotItem.setLabel('bottom', 'Pulse #')
            else:
                plw.plotItem.scatterPlot().setData(x = uniqDurs, y=[x[0] for x in meanslope], symbol='s')
                plw.plotItem.setLabel('left', 'Slope (V/s)')
                plw.plotItem.setLabel('bottom', 'Pulse Dur', 's')
        elif i == 1:
            if npul > 2:
                plw.plotItem.scatterPlot().setData(x=np.arange(npul), y=meannspk[0], symbol='o')
                plw.plotItem.setLabel('left', 'Spike Count')
                plw.plotItem.setLabel('bottom', 'Pulse #')
            else:
                plw.plotItem.scatterPlot().setData(x = uniqDurs, y=[x[0] for x in meannspk], symbol='s')
                plw.plotItem.setLabel('left', 'Spike Count')
                plw.plotItem.setLabel('bottom', 'Pulse Dur', 's')
        elif i == 2:
            if npul > 2:
                plw.plotItem.scatterPlot().setData(x=np.arange(npul), y=meanlat[0], symbol='o')
                plw.plotItem.setLabel('left', 'Latency', 's')
                plw.plotItem.setLabel('bottom', 'Pulse #')
            else:
                plw.plotItem.scatterPlot().setData(x = uniqDurs, y=[x[0] for x in meanlat], symbol='s')
                plw.plotItem.setLabel('left', 'Latency', 's')
                plw.plotItem.setLabel('bottom', 'Pulse Dur', 's')
        plw.plotItem.autoRange()
        view = plw.plotItem.viewRange()
        if view[0][1] > xmax:
            xmax = view[0][1]
        plw.plotItem.setYRange(0., view[1][1])

    for plw in plotWidget:
        plw.plotItem.setXRange(0., xmax)

