from PyQt5.QtWidgets import QPushButton, QLineEdit, QApplication, QFormLayout, QWidget, QTextEdit, QMessageBox, QSpinBox
from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.barcode.qr import QrCodeWidget 
from reportlab.graphics import renderPDF
import os

import textwrap
from datetime import datetime

from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

from sign import *


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    error = pyqtSignal(str)
    file_saved_as = pyqtSignal(str)


class Generator(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handle worker thread setup, signals
    and wrap-up.

    :param data: The data to add to the PDF for generating.
    """

    def __init__(self, data):
        super().__init__()
        self.data = data
        self.signals = WorkerSignals()

    def gen(self):
        try:
            p = Canvas(self.data['fileName'])
            p.setPageSize((400, 400))

            content= self.data['content'].replace('\n', ' ')
            #content sau nay phai ghep voi chu ky RSA
            sk, pk = generateKey()
            signature_bytes = sign_msg(bytes(content, 'utf-8'), sk)
            signature = binascii.hexlify(signature_bytes).decode('utf-8')
            qr_data = content+'#'+self.data['customer']+'#'+signature
            # Generate qr code
            qrw = QrCodeWidget(qr_data) 

            d = Drawing(10,10) 
            d.add(qrw)

            renderPDF.draw(d, p, 0, 0)
            p.showPage()
            p.save()

            # mo 1 cai pdf co san ra
            template = PdfReader(self.data['fileName'], decompress=False).pages[0]
            template_obj = pagexobj(template)

            canvas = Canvas(self.data['fileName'])

            xobj_name = makerl(canvas, template_obj)
            canvas.doForm(xobj_name)

            # Date: Todays date
            today = datetime.today()
            canvas.drawString(500, 15, today.strftime('%F'))


            # Customer
            canvas.drawString(20, 800, self.data['customer'])


            ystart = 750

            # Program Language

            comments = self.data['content'].replace('\n', ' ')
            if comments:
                lines = textwrap.wrap(comments, width=65) # 45
                first_line = lines[0]
                remainder = ' '.join(lines[1:])

                lines = textwrap.wrap(remainder, 75) # 55
                lines = lines[:4]  # max lines, not including the first.

                canvas.drawString(155, ystart, first_line)
                for n, l in enumerate(lines, 1):
                    canvas.drawString(80, ystart - (n*28), l)

            canvas.save()

        except Exception as e:
            self.signals.error.emit(str(e))
            print('error')
            return

        self.signals.file_saved_as.emit(self.data['fileName'])