import unittest
from unittest.mock import patch, MagicMock
from src.apiClients.blockchair_client import BlockchairClient


class TestBlockchairClient(unittest.TestCase):

    @patch('src.apiClients.blockchair_client.requests.get')
    def test_get_address_info_success(self, mock_get):
        # Respuesta 200 exitosa con datos simulados
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'someaddress': {'balance': 100000000, 'transaction_count': 3}
            }
        }
        mock_get.return_value = mock_response

        client = BlockchairClient(api_key='test_key')
        response = client.get_address_info('someaddress')

        self.assertEqual(response['balance'], 100000000)
        self.assertEqual(response['transaction_count'], 3)

    @patch('src.apiClients.blockchair_client.requests.get')
    def test_get_address_info_exception(self, mock_get):
        # Simulacion de fallo en la llamada API
        mock_get.side_effect = Exception("API failure")

        client = BlockchairClient(api_key='test_key')
        response = client.get_address_info('anyaddress')

        self.assertEqual(response, {})

    @patch('src.apiClients.blockchair_client.requests.get')
    def test_get_transaction_detail_cache(self, mock_get):
        # Simulacion de llamada repetida para probar caché
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'txid123': {
                    'transaction': {'time': '2025-01-01 12:00:00', 'fee': 0.0001},
                    'inputs': [],
                    'outputs': []
                }
            }
        }
        mock_get.return_value = mock_response
        client = BlockchairClient(api_key='test_key')

        detail1 = client.get_transaction_detail('txid123')
        mock_get.assert_called_once()

        mock_get.reset_mock()
        detail2 = client.get_transaction_detail('txid123')
        mock_get.assert_not_called()

        self.assertEqual(detail1, detail2)


if __name__ == '__main__':
    unittest.main()
