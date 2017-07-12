
import xml.etree.ElementTree as ET
import math
source_filename = '<xaf_filename>.xaf'
destination_filename = 'cod2_camera_anim.txt'

tree = ET.parse(source_filename)
root = tree.getroot()
el_r_x = root.findall(".//*[@name='Camera01 \ Transform \ Rotation \ X Rotation']//FVal")
el_r_y = root.findall(".//*[@name='Camera01 \ Transform \ Rotation \ Y Rotation']//FVal")
el_r_z = root.findall(".//*[@name='Camera01 \ Transform \ Rotation \ Z Rotation']//FVal")
el_p_x = root.findall(".//*[@name='Camera01 \ Transform \ Position \ X Position']//FVal")
el_p_y = root.findall(".//*[@name='Camera01 \ Transform \ Position \ Y Position']//FVal")
el_p_z = root.findall(".//*[@name='Camera01 \ Transform \ Position \ Z Position']//FVal")

coords = []


for child in el_r_x:
	degrees = repr((-1)*(math.degrees(float(child.get('v')))%360)+90)
	num_len = degrees.index('.') + 4
	coords.append({"r_x":degrees.replace('.','').ljust(num_len,'0')[:num_len]})
	#coords[i]['r_x'] = math.degrees(float(child.get('v')))
	#i += 1
				  
i = 0
for child in el_r_y:
	degrees = repr(math.degrees(float(child.get('v')))%360)
	num_len = degrees.index('.') + 4
	coords[i]['r_y'] =degrees.replace('.','').ljust(num_len,'0')[:num_len]
	i += 1
i = 0
for child in el_r_z:
	degrees =  repr(90+(math.degrees(float(child.get('v')))%360))
	num_len = degrees.index('.') + 4
	coords[i]['r_z'] = degrees.replace('.','').ljust(num_len,'0')[:num_len]
	i += 1
i = 0
for child in el_p_x:
	num_len = child.get('v').index('.') + 4
	coords[i]['p_x'] = child.get('v').replace('.','').rstrip().ljust(num_len,'0')[:num_len]
	i += 1
i = 0
for child in el_p_y:
	num_len = child.get('v').index('.') + 4
	coords[i]['p_y'] =child.get('v').replace('.','').rstrip().ljust(num_len,'0')[:num_len]
	i += 1
i = 0
for child in el_p_z:
	num_len = child.get('v').index('.') + 4
	coords[i]['p_z'] =  child.get('v').replace('.','').rstrip().ljust(num_len,'0')[:num_len]
	i += 1
   

#  print coords
f=open(destination_filename, "w")
for c in coords:
	f.write(c['r_y']+"\n0\n" +c['p_x']+"\n"+c['p_y']+"\n"+c['p_z']+"\n"+c['r_z']+"\n"+c['r_x']+"\n")
	
f.close()
    
    

