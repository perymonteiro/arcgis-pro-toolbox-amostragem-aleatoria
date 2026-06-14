# -*- coding: utf-8 -*-
import arcpy
import random
import os

class Toolbox(object):
    def __init__(self):
        self.label = "Amostragem Aleatória"
        self.alias = "amostragem_aleatoria"
        self.tools = [AmostraAleatoria]

class AmostraAleatoria(object):
    def __init__(self):
        self.label = "Criar Amostra Aleatória (fixo ou percentual)"
        self.description = (
            "Cria uma amostra aleatória sem modificar a base original. "
            "Permite escolher número fixo ou percentual e gera uma GDB de saída."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        p0 = arcpy.Parameter(
            displayName="Feature class de entrada",
            name="input_fc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        p1 = arcpy.Parameter(
            displayName="Tipo de amostragem",
            name="sample_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p1.filter.type = "ValueList"
        p1.filter.list = ["Número fixo", "Percentual"]

        p2 = arcpy.Parameter(
            displayName="Valor da amostra",
            name="sample_value",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        p3 = arcpy.Parameter(
            displayName="Pasta de saída",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input"
        )

        p4 = arcpy.Parameter(
            displayName="Nome da Geodatabase",
            name="gdb_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        p5 = arcpy.Parameter(
            displayName="Nome da feature class de saída",
            name="output_fc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )

        p6 = arcpy.Parameter(
            displayName="Seed aleatória (opcional)",
            name="seed",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input"
        )

        return [p0, p1, p2, p3, p4, p5, p6]

    def execute(self, parameters, messages):
        input_fc = parameters[0].valueAsText
        sample_type = parameters[1].valueAsText
        sample_value = parameters[2].value
        output_folder = parameters[3].valueAsText
        gdb_name = parameters[4].value
        output_fc_name = parameters[5].value
        seed = parameters[6].value

        arcpy.env.overwriteOutput = True

        if seed is not None:
            random.seed(seed)
            messages.addMessage(f"Seed utilizada: {seed}")

        total = int(arcpy.GetCount_management(input_fc)[0])
        messages.addMessage(f"Total de registros na base: {total}")

        if sample_type == "Número fixo":
            sample_size = int(sample_value)
        else:
            if sample_value <= 0 or sample_value > 100:
                raise arcpy.ExecuteError("Percentual deve estar entre 0 e 100.")
            sample_size = int(total * (sample_value / 100.0))

        if sample_size <= 0:
            raise arcpy.ExecuteError("O tamanho da amostra é inválido.")
        if sample_size > total:
            raise arcpy.ExecuteError("O tamanho da amostra é maior que o total de registros.")

        messages.addMessage(f"Tamanho final da amostra: {sample_size}")

        gdb_path = os.path.join(output_folder, f"{gdb_name}.gdb")
        if not arcpy.Exists(gdb_path):
            arcpy.CreateFileGDB_management(output_folder, gdb_name)

        output_fc = os.path.join(gdb_path, output_fc_name)

        oid_field = arcpy.Describe(input_fc).OIDFieldName

        messages.addMessage("Lendo ObjectIDs...")
        oids = []
        with arcpy.da.SearchCursor(input_fc, [oid_field]) as cursor:
            for row in cursor:
                oids.append(row[0])

        messages.addMessage("Sorteando registros aleatoriamente...")
        sample_oids = set(random.sample(oids, sample_size))

        arcpy.MakeFeatureLayer_management(input_fc, "temp_lyr")
        arcpy.SelectLayerByAttribute_management("temp_lyr", "CLEAR_SELECTION")

        messages.addMessage("Aplicando seleção...")
        chunk_size = 999
        sample_oids = list(sample_oids)

        for i in range(0, len(sample_oids), chunk_size):
            chunk = sample_oids[i:i + chunk_size]
            sql = f"{oid_field} IN ({','.join(map(str, chunk))})"
            arcpy.SelectLayerByAttribute_management("temp_lyr", "ADD_TO_SELECTION", sql)

        messages.addMessage("Criando feature class de saída...")
        arcpy.CopyFeatures_management("temp_lyr", output_fc)

        messages.addMessage("✅ Amostragem concluída com sucesso")
