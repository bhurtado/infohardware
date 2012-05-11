# *-* coding: utf-8 *-*
import os
import MySQLdb
from lxml import etree

db = MySQLdb.connect(host='192.168.100.254',user='root',passwd='pass',db='inventario')
cursor = db.cursor()


def conversor(cant,columna):
    aux=cant
    if columna=="size":
        unit = ['MB','GB']
        aux=int(cant)/(1024*1024)
        if aux > 1024:
            aux = "%s %s" % (str(aux/1024),unit[1])
        else:
            aux=str(tmem)+unit[0]
    if columna=="clock":
        aux="%d MHz" % (int(cant)/1000000)
    return aux

def obtener_datos(arbol,ruta,datos,adicionales=None):
    respuesta =[]
    num_componentes = int(arbol.xpath('count(%s)' % ruta))
    for i in xrange(num_componentes):
        intermedio={}
        cont_adicionales=0;
        for dato in datos:
            try:
                valor = arbol.xpath("%s/%s/text()" % (ruta,dato))[i]
            except:
                if adicionales!=None:
                       valor=adicionales[cont_adicionales]
                cont_adicionales+=1
            intermedio[dato]=valor;
        respuesta.append(intermedio)
    return respuesta


def buscar_n_serie(num):
    sql = "SELECT num_serie FROM equipo WHERE num_serie = %s" % num
    cursor.execute(sql)
    if cursor.fetchone():
        return True
    else:
        return False

def buscar_componente(respuesta,tabla,datos):
    
    sql = "SELECT %s FROM %s WHERE " % (respuesta,tabla)
    
    for k in datos[0].keys():
        sql = sql + "%s = '%s' AND " % (k,datos[0][k])
    sql=sql[0:-4]
    cursor.execute(sql)
    tuplas=cursor.fetchall()
    if len(tuplas)==1 and len(tuplas[0])==1:
           return tuplas[0][0]
    return tuplas
        
def insertar_componente(tabla, datos):
    num_componentes = len(datos);
    for i in xrange(num_componentes):
        sql = "INSERT INTO %s(" % tabla
        for j in datos[i].keys():
            sql = sql + "%s," % j
        sql=sql[0:-1]
        sql = sql + ") VALUES ("
        for j in datos[i].keys():
            sql = sql + "'%s'," % conversor(datos[i][j],j)
        sql=sql[0:-1]    
        sql = sql + ")"
        cursor.execute(sql)


def borrar_componente(tabla,condiciones):
    sql = "DELETE FROM %s WHERE " % tabla
    for key in condiciones:
            sql=sql+"%s='%s'," % (key,condiciones[key])
    sql=sql[0:-1]
    cursor.execute(sql)

def leer_equipo(ns):
    res=[]
    idcpu=buscar_componente("cpu_idcpu","equipo",[{"num_serie":ns}])
    res.append(["cpu:",buscar_componente("vendor,product,slot","cpu",[{"idcpu":idcpu}])])
    res.append(["placa:",buscar_componente("vendor,product","equipo",[{"num_serie":ns}])])
    res.append(["ram:",buscar_componente("size,clock","ram",[{"equipo_num_serie":ns}])])
    res.append(["hd:",buscar_componente("serial,vendor,product,description,size","hd",[{"equipo_num_serie":ns}])])
    res.append(["cd:",buscar_componente("vendor,product","cd",[{"equipo_num_serie":ns}])])
    res.append(["red:",buscar_componente("serial,vendor,product","red",[{"equipo_num_serie":ns}])])
    
    return res

def escribir_equipo(datos):

    for linea in datos:
        print linea[0]
        for comp in linea[1]:
            print escribir_componente(comp)

def escribir_componente(comp):
    txt=""
    for c in comp:
        if c!= None:
            txt+=c+" "
    return txt


def comparar_equipos(new,old):
    res = False
    for i in xrange(len(old)):
            # Miro los componenetes nuevos que se han añadido
            for j in xrange(len(new[i][1])):
                newc=new[i][1][j]
                encontrado = False
                for k in xrange(len(old[i][1])):
                    if(newc==old[i][1][k]):
                        encontrado = True
                        break;
                if encontrado==False:
                    print new[i][0]+"(+) "+escribir_componente(newc)
            # Miro los componenetes antiguos que ya no están
            for j in xrange(len(old[i][1])):
                oldc=old[i][1][j]
                encontrado = False
                for k in xrange(len(new[i][1])):
                    if(oldc==new[i][1][k]):
                        encontrado = True
                        break;
                if encontrado==False:
                    print new [i][0]+"(-) "+escribir_componente(oldc)
                    
    return res
           

        

#os.system("lshw -xml>/tmp/sys.xml")
arbol = etree.parse ("/tmp/sys.xml")


#Num serie
ns=""
while ns=="":
    ns = raw_input("Número de serie: ")
oldequipo=""
if buscar_n_serie(ns):
    oldequipo=leer_equipo(ns)
    print "Equipo ya inventariado"
else:
    print "Equipo nuevo"
print "Número de serie: "+ns

#CPU
ruta = "/node/node/node[description='CPU'][product]"
columnas = ["vendor","product","slot"]
datos=obtener_datos(arbol,ruta,columnas);
idcpu=buscar_componente("idcpu","cpu",datos)

if idcpu==0:
    insertar_componente("cpu",datos)
    idcpu=buscar_componente("idcpu","cpu",datos)


# Si el equipo esta ya inventariado: Borramos todos los componenetes guardados en la siguiente lista
if buscar_n_serie(ns):
    tablas_a_borrar = ["ram","hd","cd","red","equipo"]
    for tabla in tablas_a_borrar:
        if tabla=="equipo":
            condiciones={"num_serie":ns}
        else:
            condiciones={"equipo_num_serie":ns}
        borrar_componente(tabla,condiciones)
    
# Insertamos los restantes componentes
tablas = ["equipo","ram","hd","cd","red"]
rutas = ["/node/node[description='Motherboard']",
"/node/node/node[description='System Memory']/node[size]",
"//node[@class='disk' and @id='disk' and @handle!='']/size/..",
"//node[@class='disk' and @id='cdrom' and @handle!='']/..",
"//node[@class='network' or @class='bridge']/../node[description[contains(text(),'Eth') or contains(text(),'Wire')]][@handle!='']"]
columnas = [["vendor","product","cpu_idcpu","num_serie"],["size","clock","equipo_num_serie"],["vendor","product","description","size","serial","equipo_num_serie"],["vendor","product","equipo_num_serie"],["vendor","product","serial","equipo_num_serie"]]
for i in xrange(len(tablas)):
    if tablas[i]=="equipo":
        datos=obtener_datos(arbol,rutas[i],columnas[i],[idcpu,ns])
    else:
        datos=obtener_datos(arbol,rutas[i],columnas[i],[ns])
    insertar_componente(tablas[i],datos)



#db.commit()

newequipo=leer_equipo(ns)
escribir_equipo(newequipo)
if oldequipo!="":
    print "\nDIFERENCIAS"
    if not comparar_equipos(newequipo,oldequipo):
        print "No ha habido ningún cambio\n"
