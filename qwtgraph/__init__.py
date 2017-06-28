#!/usr/bin/env python3

import sys
import signal
import logging as log
from PyQt4 import QtGui, QtCore, Qt
import qwt
from enum import Enum

#class Color(Enum):
    #white,
    #black,
    #red,
    #darkRed,
    #green,
    #darkGreen,
    #blue,
    #darkBlue,
    #cyan,
    #darkCyan,
    #magenta,
    #darkMagenta,
    #yellow,
    #darkYellow,
    #gray,
    #darkGray,
    #lightGray

GLOBAL = []

def easypen(pen):
    #  try:
    try:
        col, size = pen.split('_')
        size = 2
    except ValueError:
        col, size = pen, 1
    col = Qt.Qt.darkYellow
    return Qt.QPen(Qt.QColor(col), size, Qt.Qt.SolidLine)
    #    except:
    #       return Qt.QPen(Qt.Qt.black, 1, Qt.Qt.SolidLine)

class DataPlot(qwt.QwtPlot):

    def __init__(self, *args):
        qwt.QwtPlot.__init__(self, *args)

        self.enableAxis(qwt.QwtPlot.xBottom, True)
        self.enableAxis(qwt.QwtPlot.yLeft, True)
        self.axisWidget(qwt.QwtPlot.yLeft).scaleDraw().setMinimumExtent(100)

    def set_data(self, datax, datay, pen):
        curve = qwt.QwtPlotCurve("Curve 1")
        curve.setRenderHint(qwt.QwtPlotItem.RenderAntialiased)
        curve.setData(datax, datay)
        curve.setPen(pen)
        curve.attach(self)

    def set_y_scale(self, smin, smax):
        self.setAxisScale(qwt.QwtPlot.yLeft, smin, smax)

    def add_vmarker(self, pos, pen):
        marker = qwt.QwtPlotMarker()
    #        marker.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        marker.setLineStyle(qwt.QwtPlotMarker.VLine)
        marker.setLinePen(pen)
        marker.setXValue(pos)
        marker.attach(self)

    def add_hmarker(self, pos, pen):
        marker = qwt.QwtPlotMarker()
    #        marker.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        marker.setLineStyle(qwt.QwtPlotMarker.HLine)
        marker.setLinePen(pen)
        marker.setYValue(pos)
        marker.attach(self)

    def redraw(self):
        self.replot()


class GraphUI(QtGui.QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QtGui.QVBoxLayout())

        self.plot = DataPlot()
        self.layout().addWidget(self.plot)
        self.setGeometry(200, 200, 1100, 650)

        GLOBAL.append(self)
        #self.plot.redraw()
        #self.show()

    def set_data(self, xdata, ydata, pen=None):
        self.plot.set_data(xdata, ydata, easypen(pen))
        self.plot.redraw()

    def add_vmarker(self, pos, pen=None):
        self.plot.add_vmarker(pos, easypen(pen))

    def add_hmarker(self, pos, pen=None):
        self.plot.add_hmarker(pos, easypen(pen))

    def add_line(self, x1, y1, x2, y2, pen):
        self.plot.set_data([x1, x2], [y1, y2], easypen(pen))


class qtapp:
    def __init__(self, active=True):
        self._active = active

    def __enter__(self, *args):
        if self._active:
            self.app = QtGui.QApplication(sys.argv)
            signal.signal(signal.SIGINT, signal.SIG_DFL)
        return self

    def __exit__(self, *args):
        pass

    def run(self):
        return self.app.exec_() if GLOBAL else None



def main():
    log.basicConfig(level=log.INFO)
    with qtapp() as app:
        w = GraphUI()
        w.show()
        app.run()

if __name__ == '__main__':
    main()

