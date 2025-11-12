from tools import clima_destino, recomendar_actividades

def test_tools():
    print("🧪 TESTEO COMPLETO DE HERRAMIENTAS\n")
    
    # Diferentes combinaciones para probar
    test_cases = [
        {"ciudad": "Barcelona", "interes": "gastronomia"},
        {"ciudad": "Roma", "interes": "historia"},
        {"ciudad": "Berlín", "interes": "aventura"},
        {"ciudad": "Londres", "interes": "naturaleza"}
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"🔍 Test {i}: {case['ciudad']} - {case['interes']}")
        print("-" * 40)
        
        # Test clima y presupuesto
        resultado_destino = clima_destino.invoke({
            "ciudad": case['ciudad'], 
            "presupuesto": 1200
        })
        print(resultado_destino)
        
        # Test actividades
        resultado_actividades = recomendar_actividades.invoke(case)
        print(resultado_actividades)
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    test_tools()
