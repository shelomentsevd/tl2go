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

class TLObject:
	name = str()
	crc = str()
	flags = False
	fields = []
	def __init__(self, name, crc, flags=False):
		self.name = name
		self.crc = crc
		self.flags = flags
	def add(self,fieldName, fieldType, chunk, flag=-1):
		self.fields.append((fieldName, fieldType, chunk, flag))
	def translate(self):
		# Structure
		print "const crc_"+self.name+" = 0x"+self.crc
		print "type TL_"+self.name+" struct {"
		for field in self.fields:
			# print field[0].capitalize(), tl2goType(field[1]), '`json:"'+field[0]+'"`', "// "+field[2]
			print field[0].capitalize(), tl2goType(field[1]), "// "+field[2]
		print "}"
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
			print "x.Int(fields)"
			for field in self.fields:
				goType = tl2goType(field[1])
				capField = field[0].capitalize()
				bitFlag = field[3] != -1
				if bitFlag:
					if goType == "bool":
						continue
					else:
						print "if flags&(1<<"+field[3]+")!=0{"
				if goType == "TL":
					print "x.Bytes(e."+capField+".encode())"
				elif goType == "[]TL":
					print "x.Vector(e." + capField + ")"
				elif goType == "[]int32":
					print "x.VectorInt(e." + capField + ")"
				elif goType == "[]int64":
					print "x.VectorLong(e." + capField + ")"
				elif goType == "[]string":
					print "x.VectorString(e." + capField + ")"
				elif goType == "int32":
					print "x.Int(e."+capField+")"
				elif goType == "int64":
					print "x.Long(e."+capField+")"
				elif goType == "float64":
					print "x.Double(e."+capField+")"
				elif goType == "string":
					print "x.String(e."+capField+")"
				else:
					raise "WRONG TYPE: "+goType
				if bitFlag:
					print "}"
				
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
			dotpos, ternpos = fieldType.find("."), fieldType.find("?")
			# bitset flag
			if dotpos != -1 and ternpos != -1:
				bit = fieldType[dotpos+1:ternpos]
				fieldType = fieldType[ternpos+1:]
				tlObj.add(fieldName, fieldType, chunk, bit)
				continue
			tlObj.add(fieldName, fieldType, chunk)
	return tlObj