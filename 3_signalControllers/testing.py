def adder(x):
   #x.printy()
    return x.a + x.b

class myClass():
    def __init__(self):
        self.a = 1
        self.b = 2
    def add(self):
        return adder(self)
    def printy(self):
        print('YAY')
        return adder(self)
