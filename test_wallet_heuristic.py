"""
test_cluster_heuristics.py
Script para probar la clasificación de direcciones Bitcoin conocidas
"""

from src.cluster_heuristics.cluster_heuristics import ClusterHeuristics
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_cluster_classification():
    """Prueba la clasificación con diferentes tipos de direcciones conocidas."""
    
    heuristics = ClusterHeuristics()
    
    # Direcciones conocidas de diferentes tipos
    test_addresses = {
        
        # Genesis Block (Satoshi)
        "genesis": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        
        # Exchanges conocidos
        "binance_1": "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
        "coinbase_1": "3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp8v",
        "bitfinex_1": "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r",
        
        # Direcciones de minería
        "f2pool": "1KFHE7w8BhaENAswwryaoccDb6qcT6DbYY",
        "antpool": "12dRugNcdxK39288NjcDV4GX7rMsKCGn6B",
        
        # Direcciones personales/pequeñas (ejemplos)
        "personal_1": "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF",
        "personal_2": "3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy",
        
        # Direcciones con mucha actividad (probables servicios)
        "high_volume_1": "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
        "high_volume_2": "3Cbq7aT1tY8kMxWLbitaG7yT6bPbKChq64",

        # Direcciones del hack de Bitfinex (2016) - Casos documentados de peeling chain
        # Dirección inicial del hack de Bitfinex
        "bitfinex_hack_main": "1EnJHhq8Jq8vDuZA5ahVh6H4t6jh1mB4rq",
        
        # Direcciones intermedias en la peel chain del hack
        "bitfinex_peel_1": "1J4yuJFqozxLWTF8FWNoVfxH3Tfh7cCvCE",
        "bitfinex_peel_2": "1AC4fMwgY8j9onSbXEWeH6Zan8QGMSdmtA",
        "bitfinex_peel_3": "1EcDvJfJXq5VKpRtQYJCYuaezLqxNyQ4vw",
        
        # Direcciones conocidas de mixers usados
        "mixer_wasabi": "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h",
        "mixer_chipmixer": "35hK24tcLEWcgNA4JxpvbkNkoAcDGqQPsP",
        
        # Direcciones pequeñas después del pelado
        "small_peel_1": "3FkenCiXpSLqD8L79intRNXUgjRoH9sjXa",
        "small_peel_2": "13kMo2gCvT5v6UgbnLBxSKKhHxBnCKWTDt",

    }
    
    results = {}
    
    print("\n" + "="*80)
    print("PRUEBA DE CLASIFICACIÓN DE DIRECCIONES BITCOIN")
    print("="*80 + "\n")
    
    for name, address in test_addresses.items():
        print(f"\n{'─'*80}")
        print(f"Probando: {name}")
        print(f"Dirección: {address}")
        print(f"{'─'*80}")
        
        try:
            result = heuristics.classify_address(address)
            results[name] = result
            
            print(f"\n✓ Resultado:")
            print(f"  • Tipo de cluster: {result['cluster_type']}")
            print(f"  • Wallet ID: {result.get('wallet_id', 'N/A')}")
            print(f"  • Confianza: {result['confidence']:.2%}")
            print(f"  • Label: {result.get('label', 'N/A')}")
            print(f"  • Descripción: {result['description']}")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            results[name] = {"error": str(e)}
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE RESULTADOS")
    print("="*80 + "\n")
    
    cluster_types = {}
    for name, result in results.items():
        if 'error' not in result:
            cluster_type = result['cluster_type']
            if cluster_type not in cluster_types:
                cluster_types[cluster_type] = []
            cluster_types[cluster_type].append(name)
    
    for cluster_type, addresses in cluster_types.items():
        print(f"\n{cluster_type.upper()}:")
        for addr in addresses:
            print(f"  • {addr}")
    
    print("\n" + "="*80 + "\n")
    
    return results


def test_specific_cluster(wallet_id: str):
    """Prueba la clasificación de un cluster específico por wallet_id."""
    
    heuristics = ClusterHeuristics()
    
    print(f"\nProbando cluster: {wallet_id}")
    print("─" * 80)
    
    try:
        result = heuristics.classify_cluster(wallet_id)
        
        print(f"\n✓ Resultado:")
        print(f"  • Tipo de cluster: {result['cluster_type']}")
        print(f"  • Confianza: {result['confidence']:.2%}")
        print(f"  • Label: {result['label']}") 
        print(f"  • Descripción: {result['description']}")
          
        
        return result
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


if __name__ == "__main__":
    # Ejecutar pruebas
    print("\n🔍 Iniciando pruebas de clasificación de direcciones...\n")
    
    # Prueba 1: Clasificación de direcciones variadas
    results = test_cluster_classification()
    
    # Prueba 2: Si quieres probar un wallet_id específico
    # test_specific_cluster("Binance-coldwallet")
    
    print("\n✅ Pruebas completadas.\n")
