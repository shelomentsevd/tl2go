#!/usr/bin/python
import sys, string

def tl2goType(tlType):
    if tlType == "true" or tlType == "false":
        return "bool"
    if tlType == "int":
        return "int32"
    if tlType == "string":
        return "string"
    if tlType == "long":
        return "int64"
    if tlType == "double":
        return "float64"
    if tlType.find("Vector") != -1:
        fpos, spos = tlType.find("<"), tlType.find(">")
        return "[]" + tl2goType(tlType[fpos + 1:spos])
    return "TL"

def encodeField(fieldName, fieldType):
    if fieldType == "TL":
        return "x.Bytes(e." + fieldName + ".encode())"
    elif fieldType == "[]TL":
        return "x.Vector(e." + fieldName + ")"
    elif fieldType == "[]int32":
        return "x.VectorInt(e." + fieldName + ")"
    elif fieldType == "[]int64":
        return "x.VectorLong(e." + fieldName + ")"
    elif fieldType == "[]string":
        return "x.VectorString(e." + fieldName + ")"
    elif fieldType == "int32":
        return "x.Int(e." + fieldName + ")"
    elif fieldType == "int64":
        return "x.Long(e." + fieldName + ")"
    elif fieldType == "float64":
        return "x.Double(e." + fieldName + ")"
    elif fieldType == "string":
        return "x.String(e." + fieldName + ")"
    else:
        raise ValueError("WRONG TYPE: " + fieldType)

def decodeField(fieldType):
    if fieldType == "TL":
        return "m.Object()"
    elif fieldType == "[]TL":
        return "m.Vector()"
    elif fieldType == "[]int32":
        return "m.VectorInt()"
    elif fieldType == "[]int64":
        return "m.VectorLong()"
    elif fieldType == "[]string":
        return "m.VectorString()"
    elif fieldType == "int32":
        return "m.Int()"
    elif fieldType == "int64":
        return "m.Long()"
    elif fieldType == "float64":
        return "m.Double()"
    elif fieldType == "string":
        return "m.String()"
    else:
        raise ValueError("WRONG TYPE: " + fieldType)

class TLObject:
    name = str()
    crc = str()
    flags = False
    fields = []
    def __init__(self, name, crc, flags=False):
        self.name = name.replace(".", "_")
        self.crc = crc
        self.flags = flags
        self.fields = []
    def add(self,fieldName, fieldType, chunk, flag=-1):
        self.fields.append((fieldName, fieldType, chunk, flag))

    def translate(self):
        self.structure()
        self.encoding()

    def structure(self):
        # Structure
        print "const crc_"+self.name+" = 0x"+self.crc
        print "type TL_"+self.name+" struct {"
        for field in self.fields:
            # print field[0].capitalize(), tl2goType(field[1]), '`json:"'+field[0]+'"`', "// "+field[2]
            print field[0].capitalize(), tl2goType(field[1]), "// "+field[2]
        print "}"

    def decoding(self):
        print "case crc_"+self.name+":"
        if self.flags:
            print "flags := m.Int()"
            # Get all fields
            for field in self.fields:
                goType = tl2goType(field[1])
                if field[3] != -1:
                    if goType == "bool":
                        if field[1] == "true":
                            print field[0]+":="+"flags&(1<<"+field[3]+")!=0"
                        else:
                            print field[0]+":="+"flags&(1<<"+field[3]+")==0"
                    else:
                        print "var "+field[0]+" "+goType
                        print "if flags&(1<<"+field[3]+")!=0{"
                        print field[0]+"="+decodeField(goType)
                        print "}"
                else:
                    print field[0] + ":=" + decodeField(goType)
            # Fill structure
            print "r = TL_" + self.name + "{"
            for field in self.fields:
                capField = field[0].capitalize()
                print capField + ":" + field[0] + ","
            print "}"
        else:
            print "r = TL_"+self.name+"{"
            for field in self.fields:
                goType = tl2goType(field[1])
                capField = field[0].capitalize()
                print capField+":"+decodeField(goType)+","
            print "}"

    def encoding(self):
        # Encoding function
        print "// Encoding TL_"+self.name
        print "func (e TL_"+self.name+") encode() []byte {"
        print "x := NewEncodeBuf(512)"
        print "x.UInt(crc_"+self.name+")"
        if self.flags:
            print "var flags int32"
            for field in self.fields:
                if field[3] == -1:
                    continue
                goType = tl2goType(field[1])
                capField = field[0].capitalize()
                if goType == "bool":
                    if field[1]=="true":
                        print "if e."+capField+"{"
                    else:
                        print "if !e."+capField+"{"
                elif goType == "int32" or goType == "int64" or goType == "float64":
                    print "if e."+capField+">0 {"
                elif goType == "string":
                    print "if e."+capField+"!=\"\"{"
                else:
                    print "if _, ok := (e."+capField+").(TL_null); !ok {"
                print "flags |= (1<<"+field[3]+")"
                print "}"
            print "x.Int(flags)"
            for field in self.fields:
                goType = tl2goType(field[1])
                capField = field[0].capitalize()
                bitFlag = field[3] != -1
                if bitFlag:
                    if goType == "bool":
                        continue
                    else:
                        print "if flags&(1<<"+field[3]+")!=0{"
                print encodeField(capField, goType)
                if bitFlag:
                    print "}"
        else:
            for field in self.fields:
                goType = tl2goType(field[1])
                capField = field[0].capitalize()
                print encodeField(capField, goType)
                
        print "return x.buf"
        print "}"

def parse(tlString):
    chunks = string.split(tlString, " ")
    # Get name and crc
    name, crc = chunks[0].split("#")
    flags = False
    chunks = chunks[1:]
    if chunks[0].find(":#") != -1:
        chunks = chunks[1:]
        flags = True
    tlObj = TLObject(name, crc, flags)
    for chunk in chunks:
        if chunk.find(":") != -1:
            fieldName, fieldType = chunk.split(":")
            # Because 'type' is reserved in Go
            if fieldName == "type":
                fieldName = "code_type"
            dotpos, ternpos = fieldType.find("."), fieldType.find("?")
            # bitset flag
            if dotpos != -1 and ternpos != -1:
                bit = fieldType[dotpos+1:ternpos]
                fieldType = fieldType[ternpos+1:]
                tlObj.add(fieldName, fieldType, chunk, bit)
                continue
            tlObj.add(fieldName, fieldType, chunk)
    return tlObj

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "tl2go [TL]"
        sys.exit()
    tlFile = sys.argv[1]

    if len(sys.argv) == 3:
        print "package "+sys.argv[2]
    else:
        print "package "+tlFile.replace(".tl", "")

    print "import \"fmt\""

    tlObjects = []
    with open(tlFile, "r") as inputfile:
        for line in inputfile:
            if line.startswith("//"):
                continue
            if line.startswith("---"):
                continue
            if len(line.lstrip()) == 0:
                continue
            # TODO: I don't know how to translate it to go
            if line.find("{X:Type}") != -1:
                continue
            tlObj = parse(line)
            tlObjects.append((line, tlObj))
        for line, tlObj in tlObjects:
            print "// "+line
            tlObj.translate()
        print "func (m *DecodeBuf) ObjectGenerated(constructor uint32) (r TL) {"
        print "switch constructor {"
        for _, tlObj in tlObjects:
            tlObj.decoding()
        print "default:"
        print "m.err = fmt.Errorf(\"Unknown constructor: %x\", constructor)"
        print "return nil"
        print "}"
        print "return"
        print "}"