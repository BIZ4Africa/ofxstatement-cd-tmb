from ofxstatement.ofx import OfxWriter

class PrettyOfxWriter(OfxWriter):
    def toxml(self):
        print("toxml")