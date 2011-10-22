#!/usr/bin/env python

"""
Python class wrapper for data fitting.
Includes the following external methods:
getFunctions returns the list of function names (dictionary keys)
FitRegion performs the fitting
Note that FitRegion will plot on top of the current data using MPlots routines
if the current curve and the current plot instance are passed.

"""
# January, 2009
# Paul B. Manis, Ph.D.
# UNC Chapel Hill
# Department of Otolaryngology/Head and Neck Surgery
# Supported by NIH Grants DC000425-22 and DC004551-07 to PBM.
# Copyright Paul Manis, 2009
#
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
"""
    Additional Terms:
    The author(s) would appreciate that any modifications to this program, or
    corrections of erros, be reported to the principal author, Paul Manis, at
    pmanis@med.unc.edu, with the subject line "PySounds Modifications".

    Note: This program also relies on the TrollTech Qt libraries for the GUI.
    You must obtain these libraries from TrollTech directly, under their license
    to use the program.
"""

import sys
import scipy
import scipy.optimize as optimize
import PySideImporter
import openopt
import numpy
import ctypes
import numpy.random
from PySide import QtGui, QtCore
from PySide.QtUiTools import QUiLoader
from metaarray import MetaArray
# from PyQt4 import Qt
# import PyQt4.Qwt5 as Qwt
# from PyQt4.Qwt5.anynumpy import *
#from sets import *

usingMPlot = False
if usingMPlot:
    import MPlot # we include plotting as part of the fitting
    plottype = 'mplot'
usingPyqtgraph = True
if usingPyqtgraph:
    import pyqtgraph
    plottype = 'pyqtgraph'

def debug_trace():
  '''Set a tracepoint in the Python debugger that works with Qt'''
  from PyQt4.QtCore import pyqtRemoveInputHook
  from pdb import set_trace
  pyqtRemoveInputHook()
  set_trace()
      
class Fitting():
    # dictionary contains:
    # name of function, function call, initial parameters, iterations, plot color, then x and y for testing
    def __init__(self):
        self.fitfuncmap = {
        'exp0'  : (self.exp0eval, [0.0, 20.0], 2000, 'k', [0, 100],
                   [1.0, 5.0], ['A0', 'tau'], None),
        'exp1'  : (self.expeval, [0.0, 0.0, 20.0], 2000, 'k', [0, 100],
                   [0.5, 1.0, 5.0], ['DC', 'A0', 'tau'], self.expevalprime),
        'exp2'  : (self.exp2eval,  [-60.0, 10.0, 5.0, 2.0, 100.0], 5000, 'k',  [0, 100],
                   [0.5, 1.0, 5.0, 1.0, 50.0], ['DC', 'A0', 'tau0', 'A1', 'tau1'], None),
        'exppow'  : (self.exppoweval,  [0.0, 1.0, 100, ], 2000, 'k',  [0, 100],
                   [0.0, 1.0, 100.0], ['DC', 'A0', 'tau'], None),
        'boltz' : (self.boltzeval,  [0.0, 1.0, -50.0, 5.0], 1200, 'r', [-100., 100.],
                   [0.5, 1.0, -25.0, 4.0],  ['DC', 'A0', 'x0', 'k'], None),
        'gauss' : (self.gausseval,  [1.0, 0.0, 0.5], 2000, 'y',  [-10., 10.],
                   [1.0, 1.0, 2.0], ['A', 'mu', 'sigma'], None),
        'line'  : (self.lineeval,  [1.0, 0.0], 500, 'r', [-10., 10.],
                   [0.0, 2.0], ['m', 'b'], None),
        'poly2' : (self.poly2eval, [1.0, 1.0, 0.0], 500, 'r', [0, 100],
                    [0.5, 1.0, 5.0], ['a', 'b', 'c'], None),
        'poly3' : (self.poly3eval, [1.0, 1.0, 1.0, 0.0], 1000, 'r', [0., 100.],
                   [0.5, 1.0, 5.0, 2.0], ['a', 'b', 'c', 'd'], None),
        'poly4' : (self.poly4eval, [1.0, 1.0, 1.0, 1.0, 0.0], 1000, 'r', [0., 100.],
                   [0.1, 0.5, 1.0, 5.0, 2.0], ['a', 'b', 'c', 'd', 'e'], None),
        'sin'   : (self.sineeval, [-1., 1.0, 4.0, 0.0], 1000, 'r', [0., 100.],
                   [0.0, 1.0, 9.0, 0.0], ['DC', 'A', 'f', 'phi'], None),
        'boltz2' : (self.boltzeval2,  [0.0, 0.5, -50.0, 5.0, 0.5, -20.0, 3.0], 1200, 'r',
                    [-100., 50.], [0.0, 0.3, -45.0, 4.0, 0.7, 10.0, 12.0],  ['DC', 'A1', 'x1', 'k1', 'A2', 'x2', 'k2'], None),
        'taucurve' : (self.taucurve,  [0.0, 200.0, 60.0, 10.0, 20.0, 60.0, 12.0], 5000, 'r',
                    [-150., 50.], [0.025, 237.0, 60.0, 12.0, 17.0, 60.0, 14.0],  
                    ['DC', 'a1', 'v1', 'k1', 'a2', 'v2', 'k2'], None),
        }
        self.fitSum2Err = 0

    def getFunctions(self):
        return(self.fitfuncmap.keys())

    def exp0eval(self, p, x, y=None, C = None):
        yd = p[0] * numpy.exp(-x/p[1])
        if y is None:
            return (yd)
        else:
            return y - yd
    
    def expeval(self, p, x, y=None, C = None):
        yd = p[0] + p[1] * numpy.exp(-x/p[2])
        if y is None:
            return (yd)
        else:
            return y - yd

    def expevalprime(self, p, x, y=None, C = None):
        ydp = p[1] * numpy.exp(-x/p[2])/(p[2]*p[2])
        yd = p[0] + p[1] * numpy.exp(-x/p[2])
        print y
        if y is None:
            return (yd, ydp)
        else:
            return (y - yd)

    def exppoweval(self, p, x, y=None, C = None):
        if C is None:
            cx = 1.0
        else:
            cx = C[0]
        yd = p[0] + p[1] * (1-numpy.exp(-x/p[2]))**cx
        if y is None:
            return (yd)
        else:
            return y - yd

    def exp2eval(self, p, x, y=None, C = None):
        yd = p[0] + p[1] * numpy.exp(-x/p[2]) + p[3] * numpy.exp(-x/p[4])
        if y == None:
            return (yd)
        else:
            return y - yd

    def boltzeval(self,p, x, y=None, C = None):
        yd = p[0] + ((p[1]-p[0])/(1 + numpy.exp((x-p[2])/p[3])))
        if y == None:
            return (yd)
        else:
            return y - yd

    def boltzeval2(self,p, x, y=None, C = None):
        yd = p[0] + p[1]/(1 + numpy.exp((x-p[2])/p[3])) + p[4]/(1 + numpy.exp((x-p[5])/p[6]))
        if y == None:
            return (yd)
        else:
            return y - yd

    def gausseval(self,p, x, y=None, C = None):
        yd = (p[0]/(p[2]*sqrt(2.0*numpy.pi)))*numpy.exp(-((x - p[1])**2.0)/(2.0*(p[2]**2.0)))
        if y == None:
            return (yd)
        else:
            return y - yd

    def lineeval(self, p, x, y=None, C = None):
        yd = p[0]*x + p[1]
        if y == None:
            return (yd)
        else:
            return y - yd

    def poly2eval(self, p, x, y=None, C = None):
        yd = p[0]*x**2.0 + p[1]*x + p[2]
        if y == None:
            return (yd)
        else:
            return y - yd

    def poly3eval(self, p, x, y=None, C = None):
        yd = p[0]*x**3.0 + p[1]*x**2.0 + p[2]*x +p[3]
        if y == None:
            return (yd)
        else:
            return y - yd

    def poly4eval(self, p, x, y=None, C = None):
        yd = p[0]*x**4.0 + p[1]*x**3.0 + p[2]*x**2.0 + p[3]*x +p[4]
        if y == None:
            return (yd)
        else:
            return y - yd

    def sineeval(self, p, x, y=None, C = None):
        yd =  p[0] + p[1]*numpy.sin((x*2.0*numpy.pi/p[2])+p[3])
        if y == None:
            return (yd)
        else:
            return y - yd

    def taucurve(self, p, x, y=None, C = None):
        """
        'DC', 'a1', 'v1', 'k1', 'a2', 'v2', 'k2'
        """
        if p[3] <= 0.0:
            p[3] = 10.0
        if p[6] <= 0.0:
            p[6] = 10.0
        if p[1] <= 0:
            p[1] = 1000.0
        if p[4] <= 0.0:
            p[4] = 1000.0
        yd = p[0]+1.0/(p[1]*numpy.exp((x+p[2])/p[3]) +p[4]*numpy.exp(-(x+p[5])/p[6]))
        if y == None:
            return (yd)
        else:
            return y - yd

    def getClipData(self, tx, data, t0, t1):
        import Utility as U
        if not isinstance(tx, list):
            tx = tx.squeeze()
        if not isinstance(data, list):
            data = data.squeeze()
        dm = U.mask(data, tx, t0, t1)
        t = U.mask(tx, tx, t0, t1)
        return(numpy.array(t), numpy.array(dm))

    def FitRegion(self, whichdata, thisaxis, tdat, ydat, t0 = None, t1 = None,
                  fitFunc = 'exp1', fitPars = None, fixedPars = None,
                  fitPlot = None, plotInstance = None, PlotType = None,
                  dataType= 'xy', bounds=None, boundsopt = 'openopt'):
        """
        To call with tdat and ydat as simple arrays:
        FitRegion(1, 0, tdat, ydat, FitFunc = 'exp1')
        e.g., the first argument should be 1, but this axis is ignored if datatype is 'xy'
        To call with one tdat and 1 ydat, each array is 1d, call with dataType='xy' (default)
        To call with one tdat and a 2-d array of ydat, use "dataType=2d"
        To call with "blocks" where there is a list of tdats and a lit of ydats, use "dataType=blocks"
        
        """
        self.fitSum2Err = 0.0
        if t0 == t1:
            if plotInstance is not None and usingMPlot:
                (x, y) = plotInstance.getCoordinates()
                t0 = x[0]
                t1 = x[1]
        if t1 is None:
            t1 = numpy.max(tdat)
        if t0 is None:
            t0 = numpy.min(tdat)
        func = self.fitfuncmap[fitFunc]
        if func is None:
            print "FitRegion: unknown function %s" % (fitFunc)
            return
        xp = []
        xf = []
        yf = []
        yn = []
        tx = []
        names = func[6]
        if fitPars is None:
            fpars = func[1]
        else:
            fpars = fitPars
        if dataType == 'blocks':
            nblock = len(ydat) # set the number of potential blocks to analyze
        else: # but if it is from a metaarray or is xy, we can have only one "block"
            nblock = 1
        for block in range(0, nblock):
            for record in whichdata: # whichdata defines the records in the block
                if dataType == 'blocks':
                    (tx, dy) = self.getClipData(tdat[block], ydat[block][record, thisaxis, :], t0, t1)
                elif dataType == '2d':
                    (tx, dy) = self.getClipData(tdat, ydat[record,:], t0, t1)
                else: # data is "x,y", where x and y are 1-d arrays
                    (tx, dy) = self.getClipData(tdat, ydat, t0, t1)
                yn.append(names)
#                print 'R: %d fitting...t=[%f - %f], ymin/max: %f %f' % (record, numpy.min(tx), numpy.max(tx), numpy.min(dy), numpy.max(dy))
                if not any(tx):
                    continue # no data in the window...
                ier = 0
                if bounds is None:
                    plsq, cov, infodict, mesg, ier = optimize.leastsq(func[0], fpars,
                                            args=(tx.astype('float64'), dy.astype('float64'), fixedPars),
                                            full_output = 1, maxfev = func[2])
                    if ier > 4:
                        print "optimize.leastsq error flag is: %d" % (ier)
                        print mesg
                else:
                    # unpack bounds
                    if boundsopt == 'openopt':
                        lb = [y[0] for y in bounds]
                        ub = [y[1] for y in bounds]
                        fopt = openopt.DFP(func[0], fpars, tx, dy, df = None, lb=lb, ub=ub)
                        r = fopt.solve('nlp:ralg', plot=0, iprint = 10)
                        plsq = r.xf
                        ier = 0
                    else:
                        plsq, cov, infodict = optimize.fmin_l_bfgs_b(func[0],  fpars, 
                                            args=(tx.astype('float64'), dy.astype('float64'), fixedPars),
                                            maxfun = func[2], bounds = bounds,
                                            approx_grad = True)
                xfit = numpy.arange(min(tx), max(tx), (max(tx)-min(tx))/100.0)
                yfit = func[0](plsq, xfit, C=fixedPars)
                yy = func[0](plsq, tx, C=fixedPars) # calculate function
                self.fitSum2Err = numpy.sum((dy - yy)**2)
                if fitPlot != None and plotInstance != None and PlotType != None:
                    self.FitPlot(xFit = xfit, yFit = yfit, fitFunc = 'exp1',
                            fitPars = plsq, plot = fitPlot, plotInstance = plotInstance, plottype = PlotType)
                xp.append(plsq) # parameter list
                xf.append(xfit) # x plot point list
                yf.append(yfit) # y fit point list
        return(xp, xf, yf, yn,) # includes names with yn and range of tx

    def FitPlot(self, xFit = None, yFit = None, fitFunc = 'exp1',
                fitPars = None, fixedPars = None, fitPlot=None, plotInstance = None, plottype = None):
        """ Plot the fit data onto the fitPlot with the specified "plot Instance".
             if there is no xFit, or some parameters are missing, we just return.
             if there is xFit, but no yFit, then we try to compute the fit with
             what we have. The plot is superimposed on the specified "fitPlot" and
             the color is specified by the function color in the fitPars list.
             """
        if xFit is None or fitPars is None or fitPlot is None or plotInstance is None or plottype is None:
            return
        func = self.fitfuncmap[fitFunc]
        if yFit is None:
            yFit = numpy.array([])
            for k in range(0, len(fitPars)):
                yFit[k] = func[0](fitPars[k], xFit[k], C=fixedPars)
        for k in range(0, len(fitPars)):
            if plottype == 'mplot':
                plotInstance.PlotLine(fitPlot, xFit[k], yFit[k], color = func[3])
            if plottype == 'pyqtgraph':
                #self.plot1.plot(data, pen=pg.intColor(c, len(dirs), maxValue=200), decimate=decimate_factor)
                plotInstance.plot(x=xFit[k], y=yFit[k], pen='r', decimate=5)

    def getFitErr(self):
        """ Return the fit error for the most recent fit
             """
        return(self.fitSum2Err)


    def expfit(self, x, y):
        """ find best fit of a single exponential function to x and y
        using the chebyshev polynomial approximation.
        returns (DC, A, tau) for fit.

        Perform a single exponential fit to data using Chebyshev polynomial method.
        Equation fit: y = a1 * exp(-x/tau) + a0
        Call: [a0 a1 tau] = expfit(x,y);
        Calling parameter x is the time base, y is the data to be fit.
        Returned values: a0 is the offset, a1 is the amplitude, tau is the time
        constant (scaled in units of x).
        Relies on routines chebftd to generate polynomial coeffs, and chebint to compute the
        coefficients for the integral of the data. These are now included in this
        .m file source.
        This version is based on the one in the pClamp manual: HOWEVER, since
        I use the bounded [-1 1] form for the Chebyshev polynomials, the coefficients are different,
        and the resulting equation for tau is different. I manually optimized the tau
        estimate based on fits to some simulated noisy data. (Its ok to use the whole range of d1 and d0
        when the data is clean, but only the first few coeffs really hold the info when
        the data is noisy.)
        NOTE: The user is responsible for making sure that the passed data is appropriate,
        e.g., no large noise or electronic transients, and that the time constants in the
        data are adequately sampled.
        To do a double exp fit with this method is possible, but more complex.
        It would be computationally simpler to try breaking the data into two regions where
        the fast and slow components are dominant, and fit each separately; then use that to
        seed a non-linear fit (e.g., L-M) algorithm.
        Final working version 4/13/99 Paul B. Manis
        converted to Python 7/9/2009 Paul B. Manis. Seems functional.
        """
        n = 30; # default number of polynomials coeffs to use in fit
        a = numpy.amin(x)
        b = numpy.amax(x)
        d0 = self.chebftd(a, b, n, x, y) # coeffs for data trace...
        d1 = self.chebint(a, b, d0, n) # coeffs of integral...
        tau = -numpy.mean(d1[2:3]/d0[2:3])
        try:
            g = numpy.exp(-x/tau)
        except:
            g = 0.0
        dg = self.chebftd(a, b, n, x, g) # generate chebyshev polynomial for unit exponential function
        # now estimate the amplitude from the ratios of the coeffs.
        a1 = self.estimate(d0, dg, 1)
        a0 = (d0[0]-a1*dg[0])/2.0         # get the offset here
        return(a0, a1, tau)#

    def estimate(self, c, d, m):
        """ compute optimal estimate of parameter from arrays of data """
        n = len(c)
        a = sum(c[m:n]*d[m:n])/sum(d[m:n]**2.0)
        return(a)

    # note : the following routine is a bottleneck. It should be coded in C.

    def chebftd(self, a, b, n, t, d):
        """ Chebyshev fit; from Press et al, p 192.
            matlab code P. Manis 21 Mar 1999
            "Given a function func, lower and upper limits of the interval [a,b], and
            a maximum degree, n, this routine computes the n coefficients c[1..n] such that
            func(x) sum(k=1, n) of ck*Tk(y) - c0/2, where y = (x -0.5*(b+a))/(0.5*(b-a))
            This routine is to be used with moderately large n (30-50) the array of c's is
            subsequently truncated at the smaller value m such that cm and subsequent
            terms are negligible."
            This routine is modified so that we find close points in x (data array) - i.e., we find
            the best Chebyshev terms to describe the data as if it is an arbitrary function.
            t is the x data, d is the y data...
            """
        bma = 0.5*(b-a)
        bpa = 0.5*(b+a)
        inc = t[1]-t[0]
        f = numpy.zeros(n)
        for k in range(0, n):
            y = numpy.cos(numpy.pi*(k+0.5)/n)
            pos = int(0.5+(y*bma+bpa)/inc)
            if  pos < 0:
                pos = 0
            if pos >= len(d)-2:
                pos = len(d)-2
            try:
                f[k]= d[pos+1]
            except:
                print "error in chebftd: k = %d (len f = %d)  pos = %d, len(d) = %d\n" % (k, len(f), pos, len(d))
                print "you should probably make sure this doesn't happen"
        fac = 2.0/n
        c=numpy.zeros(n)
        for j in range(0, n):
           sum=0.0
           for k in range(0, n):
              sum = sum + f[k]*numpy.cos(numpy.pi*j*(k+0.5)/n)
           c[j]=fac*sum
        return(c)

    def chebint(self, a, b, c, n):
        """ Given a, b, and c[1..n] as output from chebft or chebftd, and given n,
        the desired degree of approximation (length of c to be used),
        this routine computes cint, the Chebyshev coefficients of the
        integral of the function whose coeffs are in c. The constant of
        integration is set so that the integral vanishes at a.
        Coded from Press et al, 3/21/99 P. Manis (Matlab)
        Python translation 7/8/2009 P. Manis
        """
        sum = 0.0
        fac = 1.0
        con = 0.25*(b-a) # factor that normalizes the interval
        cint = numpy.zeros(n)
        for j in range(1,n-2):
            cint[j]=con*(c[j-1]-c[j+1])/j
            sum = sum + fac * cint[j]
            fac = - fac
        cint[n-1] = con*c[n-2]/(n-1)
        sum = sum + fac*cint[n-1]
        cint[0] = 2.0*sum # set constant of integration.
        return(cint)

# routine to flatten an array/list.
#
    def flatten(self, l, ltypes=(list, tuple)):
        i = 0
        while i < len(l):
            while isinstance(l[i], ltypes):
                if not l[i]:
                    l.pop(i)
                    if not len(l):
                        break
                else:
                   l[i:i+1] = list(l[i])
            i += 1
        return l
    # flatten()


# run tests if we are "main"

if __name__ == "__main__":
#    import matplotlib.pyplot as pyplot
    import timeit
    import Fitting
    import matplotlib.pylab as MP
    Fits = Fitting.Fitting()
    x = arange(0, 100.0, 0.1)
    y = 5.0-2.5*numpy.exp(-x/5.0)+0.5*random.randn(len(x))
    (dc, aFit,tauFit) = Fits.expfit(x,y)
    yf = dc + aFit*numpy.exp(-x/tauFit)
 #   pyplot.figure(1)
  #  pyplot.plot(x,y,'k')
  #  pyplot.hold(True)
  #  pyplot.plot(x, yf, 'r')
  #  pyplot.show()

    # run tests for each type of fit, return results to compare parameters

    for func in Fits.fitfuncmap:

        print "Function: %s\nInitial: " % (func),
        f = Fits.fitfuncmap[func]
        for k in range(0,len(f[1])):
            print "%f " % (f[1][k]),
        print "\nTrue:     ",
        for k in range(0,len(f[5])):
            print "%f " % (f[5][k]),

        nstep = 20.0
        if func == 'sin':
            nstep = 100.0
        x = numpy.array(arange(f[4][0], f[4][1], (f[4][1] - f[4][0])/nstep))
        y = f[0](f[5], x)

        yd = numpy.array(y)
        my = numpy.amax(yd)
       # yd = yd + sigmax*0.05*my*(numpy.random.random_sample(shape(yd))-0.5)
        (fpar, xf, yf, names) = Fits.FitRegion(array([1]), 0, x, yd, fitFunc = func)
        #print fpar
        outstr = ""
        s = numpy.shape(fpar)
        j = 0
        outstr = ""
        for i in range(0, len(names[j])):
#            print "%f " % fpar[j][i],
            outstr = outstr + ('%s = %f, ' % (names[j][i], fpar[j][i]))
        print( "\nFIT(%d): %s" % (j, outstr) )
        if func is 'taucurve':
            MP.figure()
            MP.plot(array(x), yd, 'ro')
            MP.hold(True)
            MP.plot(xf[0], yf[0], 'b-')
            MP.show()