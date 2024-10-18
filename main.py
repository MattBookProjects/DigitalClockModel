import time
import threading
import pygame


# CONSTANTS ####################################################################################

BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREY = (40, 40, 40)
LIGHT_GREY = (80, 80, 80)
BLUE = (0, 0, 255)

DISPLAY_BLOCK_SIZE = 40
ACTIVE_COLOR = RED
INACTIVE_COLOR = GREY
BG_COLOR = BLACK
BUTTON_COLOR = LIGHT_GREY
PANEL_COLOR = BLUE


# UTILS #########################################################################

def valueToBitList(val):
    list = []
    i = 7
    while i >= 0:
        if val >= 2**i:
            list.append(1)
            val = val - 2**i
        else:
            list.append(0)
        i = i - 1
    return list

def bitListToValue(bit_list):
    val = 0
    i = 7
    for bit in bit_list:
        if bit == 1:
            val = val + 2**i
        i = i - 1
    return val

# MICROCONTROLLER ##############################################################################

class Microcontroller():
    def __init__(self):
        self.acc = 0        #AKUMULATOR (ACC/ A)
        self.registers = [[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0 ], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]] #REJESTRY PROCESORA, 4 BANKI RAZY 8 REJESTRÓW
        self.register_bank = 0  #WYBRANY BANK REJESTRÓW
        self.ports = [[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]] #4 PORTY PO 8 BITÓW
        self.int = [0, 0] #DWA WEJŚCIA NA PRZERWANIA    IE0, IE1
        self.ex = [0, 0] #DWIE FLAGI WŁĄCZENIA OBSŁUGI PRZERWAŃ     EX0, EX1
        self.carry_flag = 0 #CARRY FLAG


#FUNKCJE WBUDOWANE MIKROPROCESORA
    def setRegisterBank(self, x):   #WYBRANIE NOWEGO BANKU REJESTRÓW: MOV RS0, reg_num
        if x < 4 and x >= 0:
            self.register_bank = x
    
    def movRegToAcc(self, reg_num):     #MOV ACC, R(reg_num)
        self.acc = self.registers[self.register_bank][reg_num]
    
    def movAccToReg(self, reg_num):     #MOV R(reg_num), ACC
        self.registers[self.register_bank][reg_num] = self.acc

    def movPortToAcc(self, port_num):   #MOV ACC, P(port_num)
        self.acc = bitListToValue(self.ports[port_num])

    def movAccToPort(self, port_num):   #MOV P(port_num), ACC
        self.ports[port_num] = valueToBitList(self.acc)

    def movValToReg(self, reg_num, val):    #MOV R(reg_num), #val
        self.registers[self.register_bank][reg_num] = val
    
    def addReg(self, reg_num):      #ADD A, R(reg_num)
        self.acc = self.acc + self.registers[self.register_bank][reg_num]
        if self.acc > 255:
            self.acc = self.acc - 256
            self.carry_flag = 1
        else:
            self.carry_flag = 0
        
    def addcReg(self, reg_num):     #ADDC A, R(reg_num)
        self.acc = self.acc + self.registers[self.register_bank][reg_num] + self.carry_flag
        if self.acc > 255:
            self.acc = self.acc - 256
            self.carry_flag = 1
        else:
            self.carry_flag = 0

    def subbReg(self, reg_num):     #SUBB A, R(reg_num)
        self.acc = self.acc - self.registers[self.register_bank][reg_num] - self.carry_flag
        if self.acc < 0:
            self.acc = self.acc + 256
            self.carry_flag = 1
        else:
            self.carry_flag = 0

    def subbVal(self, val):        #SUBB A, #val
        self.acc = self.acc - val
        if self.acc < 0:
            self.acc = self.acc + 256
            self.carry_flag = 1
        else:
            self.carry_flag = 0

    def clrCarry(self):         #CLR C
        self.carry_flag = 0

#    def clrInt(self, num):      #CLR 
 #       self.int[num] = 0

    def setEx(self, num):       #SETB EX(num)
        self.ex[num] = 1

    def clrEx(self, num):       #CLR EX(num)
        self.ex[num] = 0

    def incAcc(self):           #INC A
        self.acc = self.acc + 1

    def decAcc(self):           #DEC A
        self.acc = self.acc - 1

    def setBitPort(self, port, bit):    #SETB (PORT (port), BIT (bit) ADDRESS)
        self.ports[port][bit] = 1

    def clrBitPort(self, port, bit):   #CLR (PORT (port), BIT (bit) ADDRESS)
        self.ports[port][bit] = 0

    def anlVal(self, val):          #ANL A, #val
        acc_bits = valueToBitList(self.acc)
        val_bits = valueToBitList(val)
        res_bits = []
        for i in range(8):
            if acc_bits[i] == 1 and val_bits[i] == 1:
                res_bits.append(1)
            else:
                res_bits.append(0)
        self.acc = bitListToValue(res_bits)

    def orlVal(self, val):      #ORL A, #val
        acc_bits = valueToBitList(self.acc)
        val_bits = valueToBitList(val)
        res_bits = []
        for i in range(8):
            if acc_bits[i] == 1 or val_bits[i] == 1:
                res_bits.append(1)
            else:
                res_bits.append(0) 
        self.acc = bitListToValue(res_bits)


    def swap(self):             #SWAP A
        bits = valueToBitList(self.acc)
        new_bits = bits[4:]
        new_bits.extend(bits[0:4])
        value = bitListToValue(new_bits)
        self.acc = value

# FUNKCJE ZDEFINIOWANE W PROGRAMIE
    def run(self):          #URUCHOMIENIE PROGRAMU
        self.setEx(0)
        self.setEx(1)
        while True:
            self.refreshPorts()
            self.checkInterrupts()
           

    def checkInterrupts(self):      #SPRAWDZENIE CZY POJAWIŁY SIĘ PRZERWANIA I EWEUNTALNE WYWOŁANIE ICH OBSŁUGI
        if self.int[0] == 1:
            if self.ex[0] == 1:
                self.int0()
            self.int[0] = 0
        elif self.int[1] == 1:
            if self.ex[1] == 1:
                self.int1()
            self.int[1] = 0
    

    def int0(self):             #OBSŁUGA PRZERWANIA 0 (OSCYLATOR)
        self.incSecsOnes()
        self.refreshPorts()
        
       

    def toggleMode(self):       #ZMIANA TRYBU MIĘDZY WYŚWIETLANIEM AKTUALNEJ GODZINY A TRYBEM USTAWIANIA GODZINY
        self.setRegisterBank(1)
        self.movRegToAcc(0)
        if self.acc == 0:
            self.movValToReg(0, 1)
            self.clrEx(0)
        else:
            self.movValToReg(0, 0)
            self.setEx(0)
            self.movValToReg(1, 0)
        self.setRegisterBank(0)

    def incSecsOnes(self):      #ZWIĘKSZENIE WARTOŚCI JEDNOSTEK SEKUND O 1
        self.movRegToAcc(0)
        self.incAcc()
        self.movAccToReg(7)
        self.subbVal(10)
        if (self.acc == 0):
            self.movAccToReg(0)
            self.incSecsTens()
        else:
            self.movRegToAcc(7)
            self.movAccToReg(0)
    
    def incSecsTens(self):      #ZWIĘKSZENIE WARTOŚCI DZIESIĄTEK SEKUND O 1
        self.movRegToAcc(1)
        self.incAcc()
        self.movAccToReg(7)
        self.subbVal(6)
        if (self.acc == 0):
            self.movAccToReg(1)
            self.setRegisterBank(1)
            self.movRegToAcc(0)
            self.setRegisterBank(0)
            if self.acc == 0:
                self.incMinsOnes()
        else:
            self.movRegToAcc(7)
            self.movAccToReg(1)

    def incMinsOnes(self):  #ZWIĘKSZENIE WARTOŚCI JEDNOSTEK MINUT O 1
        self.movRegToAcc(2)
        self.incAcc()
        self.movAccToReg(7)
        self.subbVal(10)
        if(self.acc == 0):
            self.movAccToReg(2)
            self.incMinsTens()
        else:
            self.movRegToAcc(7)
            self.movAccToReg(2)
    

    def incMinsTens(self):  #ZWIĘKSZENIE WARTOŚCI DZIESIĄTEK MINUT O 1
        self.movRegToAcc(3)
        self.incAcc()
        self.movAccToReg(7)
        self.subbVal(6)
        if(self.acc == 0):
            self.movAccToReg(3)
            self.setRegisterBank(1)
            self.movRegToAcc(0)
            self.setRegisterBank(0)
            if self.acc == 0:
                self.incHoursOnes()
        else:
            self.movRegToAcc(7)
            self.movAccToReg(3)

    def incHoursOnes(self): #ZWIĘKSZENIE WARTOŚCI JEDNOSTEK GODZIN O 1
        self.movRegToAcc(4)
        self.incAcc()
        self.movAccToReg(7)
        self.subbVal(10)
        if(self.acc == 0):
            self.movAccToReg(4)
            self.incHoursTens()
        else:
            self.movRegToAcc(7)
            self.subbVal(4)
            if self.acc == 0:
                self.movRegToAcc(5)
                self.subbVal(2)
                if self.acc == 0:
                    self.movAccToReg(4)
                    self.movAccToReg(5)
                else:
                    self.movRegToAcc(7)
                    self.movAccToReg(4)
            else:
                self.movRegToAcc(7)
                self.movAccToReg(4)


    def incHoursTens(self):  #ZWIĘKSZENIE WARTOŚCI DZIESIĄTEK GODZIN O 1
        self.movRegToAcc(5)
        self.incAcc()
        self.movAccToReg(5)


    def decSecsOnes(self):  #ZMNIEJSZENIE WARTOŚCI JEDNOSTEK SEKUND O 1
        self.movRegToAcc(0)
        if self.acc == 0:
            self.movValToReg(0, 9)
            self.decSecsTens()
        else:
            self.decAcc()
            self.movAccToReg(0)

    def decSecsTens(self):  #ZMNIEJSZENIE WARTOŚCI DZIESIĄTEK SEKUND O 1
        self.movRegToAcc(1)
        if self.acc == 0:
            self.movValToReg(1, 5)
        else:
            self.decAcc()
            self.movAccToReg(1)


    def decMinsOnes(self):  #ZMNIEJSZENIE WARTOŚCI JEDNOSTEK MINUT O 1
        self.movRegToAcc(2)
        if self.acc == 0:
            self.movValToReg(2, 9)
            self.decMinsTens()
        else:
            self.decAcc()
            self.movAccToReg(2)  


    def decMinsTens(self):   #ZMNIEJSZENIE WARTOŚCI DZIESIĄTEK MINUT O 1
        self.movRegToAcc(3)
        if self.acc == 0:
            self.movValToReg(3, 5)
        else:
            self.decAcc()
            self.movAccToReg(3)


    def decHoursOnes(self):  #ZMNIEJSZENIE WARTOŚCI JEDNOSTEK GODZIN O 1
        self.movRegToAcc(4)
        if self.acc == 0:
            self.movRegToAcc(5)
            if self.acc == 0:
                self.movValToReg(4, 3)
                self.movValToReg(5, 2)   
            else:
                self.movValToReg(4, 9)
                self.decHoursTens()
        else:
            self.decAcc()
            self.movAccToReg(4)     

 
    def decHoursTens(self):  #ZMNIEJSZENIE WARTOŚCI DZIESIĄTEK GODZIN O 1
        self.movRegToAcc(5)
        self.decAcc()
        self.movAccToReg(5) 


    def switchEditedValue(self):    #PRZEŁĄCZ EDYTOWANĄ WARTOŚĆ
        self.setRegisterBank(1)
        self.movRegToAcc(1)
        self.setRegisterBank(0)
        self.incAcc()
        self.movAccToReg(7)
        self.subbVal(3)
        if self.acc != 0:
            self.movRegToAcc(7)
        self.setRegisterBank(1)
        self.movAccToReg(1)
        self.setRegisterBank(0)



    def int1(self):         #OBSŁUGA PRZERWANIA 1 (PANEL KONTROLNY)
        self.movPortToAcc(3)
        self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
        self.subbVal(1)
        if self.acc == 0:
            self.toggleMode()
        else:
            self.setRegisterBank(1)
            self.movRegToAcc(0)
            self.setRegisterBank(0)
            if self.acc != 0:
                self.movPortToAcc(3)
                self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
                self.subbVal(2)
                if self.acc == 0:
                   self.switchEditedValue()
                else:
                    self.movPortToAcc(3)
                    self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
                    self.subbVal(3)
                    if self.acc == 0:
                        self.setRegisterBank(1)
                        self.movRegToAcc(1)
                        self.setRegisterBank(0)
                        if self.acc == 0:
                            self.decHoursOnes()
                        else:
                            self.setRegisterBank(1)
                            self.movRegToAcc(1)
                            self.setRegisterBank(0)
                            self.subbVal(1)
                            if self.acc == 0:
                                self.decMinsOnes()
                            else:
                                self.decSecsOnes()
                        
                    else:
                        self.movPortToAcc(3)
                        self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
                        self.subbVal(4)
                        if self.acc == 0:
                            self.setRegisterBank(1)
                            self.movRegToAcc(1)
                            self.setRegisterBank(0)
                            self.movAccToReg(7)
                            if self.acc == 0:
                                self.incHoursOnes()
                            else:
                                self.movRegToAcc(7)
                                self.subbVal(1)
                                if self.acc == 0:
                                    self.incMinsOnes()
                                else:
                                    self.incSecsOnes()


        self.movPortToAcc(3)
        self.anlVal(bitListToValue([1, 1, 1, 1, 0, 0, 0, 0]))
        self.movAccToPort(3)
        


   


    def refreshPorts(self):             #ODŚWIEŻ WARTOŚĆ NA PORTACH
        self.movRegToAcc(1)
        self.swap()
        self.movAccToReg(7)
        self.movRegToAcc(0)
        self.addReg(7)
        self.movAccToPort(0)
        self.movRegToAcc(3)
        self.swap()
        self.movAccToReg(7)
        self.movRegToAcc(2)
        self.addReg(7)
        self.movAccToPort(1)
        self.movRegToAcc(5)
        self.swap()
        self.movAccToReg(7)
        self.movRegToAcc(4)
        self.addReg(7)
        self.movAccToPort(2)
        self.setRegisterBank(1)
        self.movRegToAcc(0)
        self.setRegisterBank(0)
        if self.acc != 0:
            self.setRegisterBank(1)
            self.movRegToAcc(1)
            self.setRegisterBank(0)
            self.movAccToReg(7)
            if self.acc == 0:
                self.movPortToAcc(3)
                self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
                self.orlVal(bitListToValue([0, 0, 0, 1, 0, 0, 0, 0]))
                self.movAccToPort(3)
            else:
                self.movRegToAcc(7)
                self.subbVal(1)
                if self.acc == 0:
                    self.movPortToAcc(3)
                    self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
                    self.orlVal(bitListToValue([0, 0, 1, 0, 0, 0, 0, 0]))
                    self.movAccToPort(3)
                else:
                    self.movPortToAcc(3)
                    self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
                    self.orlVal(bitListToValue([0, 0, 1, 1, 0, 0, 0, 0]))
                    self.movAccToPort(3)
        else:
            self.movPortToAcc(3)
            self.anlVal(bitListToValue([0, 0, 0, 0, 1, 1, 1, 1]))
            self.movAccToPort(3)
            

   

   

class Display():

    def __init__(self, microcontroller, screen, x , y):
        self.microcontroller = microcontroller
        self.segments = [[0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0]]
        self.screen = screen
        self.x = x
        self.y = y
        self.blinking = 0
        self.blinkPhase = 0

    def refresh(self):          #ODŚWIEŻ NA PODSTAWIE WARTOŚCI NA WEJŚCIACH
        self.blinking = bitListToValue([0, 0, 0, 0] + self.microcontroller.ports[3][:4]) 
        for i in range(2, -1, -1):
            for j in range(2):
                if self.microcontroller.ports[i][4*j+0] or self.microcontroller.ports[i][4*j+2] or self.microcontroller.ports[i][4*j+1] and self.microcontroller.ports[i][4*j+3] or not self.microcontroller.ports[i][4*j+1] and not self.microcontroller.ports[i][4*j+3]:
                    self.segments[(2-i)*2 + j][0] = 1
                else:
                    self.segments[(2-i)*2 + j][0] = 0
                if self.microcontroller.ports[i][4*j+0] or self.microcontroller.ports[i][4*j+1] and not (self.microcontroller.ports[i][4*j+2] and self.microcontroller.ports[i][4*j+3]) or (not self.microcontroller.ports[i][4*j+2]) and (not self.microcontroller.ports[i][4*j+3]):
                    self.segments[(2-i)*2 + j][1] = 1
                else:
                    self.segments[(2-i)*2 + j][1] = 0
                if self.microcontroller.ports[i][4*j+0] or not self.microcontroller.ports[i][4*j+1] or self.microcontroller.ports[i][4*j+2] and self.microcontroller.ports[i][4*j+3] or (not self.microcontroller.ports[i][4*j+2]) and (not self.microcontroller.ports[i][4*j+3]):
                    self.segments[(2-i)*2 + j][2] = 1
                else:
                    self.segments[(2-i)*2 + j][2] = 0
                if self.microcontroller.ports[i][4*j+0] or self.microcontroller.ports[i][4*j+2] and not(self.microcontroller.ports[i][4*j+1] and self.microcontroller.ports[i][4*j+3]) or self.microcontroller.ports[i][4*j+1] and not(self.microcontroller.ports[i][4*j+2] and self.microcontroller.ports[i][4*j+3]):
                    self.segments[(2-i)*2 + j][3] = 1
                else:
                    self.segments[(2-i)*2 + j][3] = 0
                if (not self.microcontroller.ports[i][4*j+3]) and ((not self.microcontroller.ports[i][4*j+1]) and ( not self.microcontroller.ports[i][4*j+2]) or (not self.microcontroller.ports[i][4*j+0]) and self.microcontroller.ports[i][4*j+2]):
                     self.segments[(2-i)*2 + j][4] = 1
                else:
                    self.segments[(2-i)*2 + j][4] = 0
                if self.microcontroller.ports[i][4*j+0] or self.microcontroller.ports[i][4*j+1] or not self.microcontroller.ports[i][4*j+2] or self.microcontroller.ports[i][4*j+3]:
                    self.segments[(2-i)*2 + j][5] = 1
                else:
                    self.segments[(2-i)*2 + j][5] = 0
                if self.microcontroller.ports[i][4*j+0] or (not self.microcontroller.ports[i][4*j+1]) and (self.microcontroller.ports[i][4*j+2] or not self.microcontroller.ports[i][4*j+3]) or self.microcontroller.ports[i][4*j+1] and not self.microcontroller.ports[i][4*j+2] and self.microcontroller.ports[i][4*j+3] or self.microcontroller.ports[i][4*j+2] and not self.microcontroller.ports[i][4*j+3]:
                    self.segments[(2-i)*2 + j][6] = 1
                else:
                    self.segments[(2-i)*2 + j][6] = 0

       

    def draw(self):
        
        self.screen.fill(BG_COLOR)
        pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + 10*DISPLAY_BLOCK_SIZE, self.y + 2*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
        pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + 10*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
        pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + 22*DISPLAY_BLOCK_SIZE, self.y + 2*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
        pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + 22*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
        for i in range(6):
            if i // 2 + 1 == self.blinking and self.blinkPhase == 0:
                pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 0)*DISPLAY_BLOCK_SIZE, self.y + 1*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 3)*DISPLAY_BLOCK_SIZE, self.y + 1* DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y + 3 * DISPLAY_BLOCK_SIZE, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + ( 5*i + (i // 2 * 2 ) + 0)*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 3)*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y + 6 * DISPLAY_BLOCK_SIZE, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                

            else:
                if self.segments[i][0]:
                    pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                else:
                    pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                if self.segments[i][1]:
                    pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + ( 5*i + (i // 2 * 2 ) + 0)*DISPLAY_BLOCK_SIZE, self.y + 1*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                else:
                    pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 0)*DISPLAY_BLOCK_SIZE, self.y + 1*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                if self.segments[i][2]:
                    pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 3)*DISPLAY_BLOCK_SIZE, self.y + 1* DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                else:
                    pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 3)*DISPLAY_BLOCK_SIZE, self.y + 1* DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                if self.segments[i][3]:
                    pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y + 3 * DISPLAY_BLOCK_SIZE, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                else:
                    pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y + 3 * DISPLAY_BLOCK_SIZE, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                if self.segments[i][4]:
                    pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + ( 5*i + (i // 2 * 2 ) + 0)*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                else:
                    pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + ( 5*i + (i // 2 * 2 ) + 0)*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                if self.segments[i][5]:
                    pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 3)*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                else:
                    pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 3)*DISPLAY_BLOCK_SIZE, self.y + 4*DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE))
                if self.segments[i][6]:
                    pygame.draw.rect(self.screen, ACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y + 6 * DISPLAY_BLOCK_SIZE, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))
                else:
                    pygame.draw.rect(self.screen, INACTIVE_COLOR, (self.x + (5*i + (i // 2 * 2 ) + 1)*DISPLAY_BLOCK_SIZE, self.y + 6 * DISPLAY_BLOCK_SIZE, 2 * DISPLAY_BLOCK_SIZE, DISPLAY_BLOCK_SIZE))




class Button:
    def __init__(self, microcontroller, code, pos_x, pos_y, screen, symbolDraw):
        self.microcontroller = microcontroller
        self.code = code
        self.x = pos_x
        self.y = pos_y
        self.screen = screen
        self.symbolDraw = symbolDraw
        
    def pressed(self):          #WCIŚNIĘCIE PRZYCISKU
        self.microcontroller.ports[3][4:] = valueToBitList(self.code)[4:]
        self.microcontroller.int[1] = 1


    def draw(self):             #FUNKCJA WYŚWIETLAJĄCA PRZYCISK
        pygame.draw.rect(self.screen, BUTTON_COLOR, ((self.x, self.y, 2*DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE)))
        self.symbolDraw(self.x, self.y, self.screen)


#FUNKCJE RYSUJĄCE ODPOWIEDNI SYMBOL NA PRZYCISKACH
        
def symbolDrawStartStop(x, y, screen):
    pygame.draw.rect(screen, BLACK, (x + 2 * DISPLAY_BLOCK_SIZE / 3, y + 2 * DISPLAY_BLOCK_SIZE / 3, 2* DISPLAY_BLOCK_SIZE / 3,  2*DISPLAY_BLOCK_SIZE / 3))


def symbolDrawNext(x, y, screen):
    pygame.draw.polygon(screen, BLACK, ((x + 2 * DISPLAY_BLOCK_SIZE / 3, y + 2 * DISPLAY_BLOCK_SIZE / 3), (x + 4 * DISPLAY_BLOCK_SIZE / 3, y + DISPLAY_BLOCK_SIZE), (x + 2 * DISPLAY_BLOCK_SIZE / 3, y + 4 * DISPLAY_BLOCK_SIZE / 3)))

def symbolDrawPlus(x, y, screen):
    pygame.draw.rect(screen, BLACK, (x + 4* DISPLAY_BLOCK_SIZE / 5, y + 2 * DISPLAY_BLOCK_SIZE / 5, 2 * DISPLAY_BLOCK_SIZE / 5, 6 * DISPLAY_BLOCK_SIZE / 5))
    symbolDrawMinus(x, y, screen)


def symbolDrawMinus(x, y, screen):
    pygame.draw.rect(screen, BLACK, (x + 2*DISPLAY_BLOCK_SIZE / 5, y + 4 * DISPLAY_BLOCK_SIZE / 5, 6 * DISPLAY_BLOCK_SIZE/5, 2*DISPLAY_BLOCK_SIZE / 5 ))


class ControlPanel:             #PANEL KONTROLNY
    def __init__(self, screen,  microcontroller, x , y):
        self.microcontroller = microcontroller
        self.screen = screen
        self.x = x
        self.y = y
        self.buttons = [Button(microcontroller, 1, self.x + DISPLAY_BLOCK_SIZE, self.y + DISPLAY_BLOCK_SIZE, screen, symbolDrawStartStop),
                        Button(microcontroller, 2, self.x + 4 * DISPLAY_BLOCK_SIZE, self.y + DISPLAY_BLOCK_SIZE, screen, symbolDrawNext),
                        Button(microcontroller, 3, self.x + 7 * DISPLAY_BLOCK_SIZE, self.y + DISPLAY_BLOCK_SIZE, screen, symbolDrawMinus),
                        Button(microcontroller, 4, self.x + 10 * DISPLAY_BLOCK_SIZE, self.y + DISPLAY_BLOCK_SIZE, screen, symbolDrawPlus)]
    
    def draw(self):
        pygame.draw.rect(self.screen, PANEL_COLOR, (self.x, self.y, 13 * DISPLAY_BLOCK_SIZE, 4 * DISPLAY_BLOCK_SIZE))
        for button in self.buttons:
            button.draw()


        

#RÓWNOLEGŁE DZIAŁANIE ELEMENTÓW #########


def clockThread(microcontroller):       #OSCYLATOR WYSYŁA SYGNAŁ CO SEKUNDĘ
    while True:
        time.sleep(1)
        microcontroller.int[0] = 1
 

    
def microcontrollerThread(microcontroller): #MIKROKONTROLER
    microcontroller.run()


def displayThread(display):         #WYŚWIETLACZ ODŚWIEŻA SIĘ CAŁY CZAS NA PODSTAWIE WARTOŚCI NA WYJŚCIU PORTÓW
    while True:
        display.refresh()

def blinkingThread(display):        #MIGANIE WYŚWIETLACZA PODCZAS ZMIANY GODZINY
    while True:
        if display.blinking > 0:
            display.blinkPhase = 1
            time.sleep(0.5)
            display.blinkPhase = 0
            time.sleep(0.5)


def drawThread(screen, display, controlPanel):  #RYSOWANIE UKŁADU
    while True:
        screen.fill(BLACK)
        display.draw()
        controlPanel.draw()
        pygame.display.update()

def checkForClickThread(controlPanel):      #SPRAWDZANIE CZY PRZYCISKI SĄ WCIŚNIĘTE
    while True:
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.pos[1] >= controlPanel.y + DISPLAY_BLOCK_SIZE and event.pos[1] <= controlPanel.y + 3*DISPLAY_BLOCK_SIZE:
                    for button in controlPanel.buttons:
                        if event.pos[0] >= button.x and event.pos[0] <= button.x + 2*DISPLAY_BLOCK_SIZE:
                            button.pressed()
                           


def main():
    screen = pygame.display.set_mode((DISPLAY_BLOCK_SIZE*37, DISPLAY_BLOCK_SIZE*17))
    microcontroller = Microcontroller()
    display = Display(microcontroller, screen, 2*DISPLAY_BLOCK_SIZE, 2*DISPLAY_BLOCK_SIZE)
    control_panel = ControlPanel(screen, microcontroller, 12 * DISPLAY_BLOCK_SIZE, 11*DISPLAY_BLOCK_SIZE)
    clockT = threading.Thread(target=clockThread, args=[microcontroller])
    microcontrollerT = threading.Thread(target=microcontrollerThread, args=[microcontroller])
    displayT = threading.Thread(target=displayThread, args=[display])
    drawT = threading.Thread(target=drawThread, args=[screen, display, control_panel])
    checkForClickT = threading.Thread(target=checkForClickThread, args=[control_panel])
    blinkingT = threading.Thread(target=blinkingThread, args=[display])
  
    microcontrollerT.start()
    clockT.start()
    displayT.start()
    drawT.start()
    checkForClickT.start()
    blinkingT.start()
    


main()


