import unittest
from unittest.mock import patch, MagicMock
from src.apiClients.walletexplorer_client import WalletExplorerClient


class TestWalletExplorerClient(unittest.TestCase):

    @patch('src.apiClients.walletexplorer_client.requests.get')
    def test_get_wallet_id_from_address_found(self, mock_get):
        print("Probando: get_wallet_id_from_address con wallet encontrado")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'found': True,
            'wallet_id': 'wallet123'
        }
        mock_get.return_value = mock_response

        client = WalletExplorerClient()
        wallet_id = client.get_wallet_id_from_address('someaddress')
        self.assertEqual(wallet_id, 'wallet123')

    @patch('src.apiClients.walletexplorer_client.requests.get')
    def test_get_wallet_id_from_address_not_found(self, mock_get):
        print("Probando: get_wallet_id_from_address sin wallet encontrado")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'found': False}
        mock_get.return_value = mock_response

        client = WalletExplorerClient()
        wallet_id = client.get_wallet_id_from_address('someaddress')
        self.assertIsNone(wallet_id)

    @patch('src.apiClients.walletexplorer_client.requests.get')
    def test_get_wallet_id_from_address_raise_exception(self, mock_get):
        print("Probando: get_wallet_id_from_address lanza excepción por error HTTP")
        mock_get.side_effect = Exception("Request failed")

        client = WalletExplorerClient()
        with self.assertRaises(Exception):
            client.get_wallet_id_from_address('someaddress')

    @patch('src.apiClients.walletexplorer_client.requests.get')
    def test_get_wallet_transactions_success(self, mock_get):
        print("Probando: get_wallet_transactions con respuesta exitosa")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'txs': ['tx1', 'tx2']}
        mock_get.return_value = mock_response

        client = WalletExplorerClient()
        data = client.get_wallet_transactions('wallet123')
        self.assertIn('txs', data)
        self.assertEqual(len(data['txs']), 2)

    @patch('src.apiClients.walletexplorer_client.requests.get')
    def test_get_wallet_transactions_exception(self, mock_get):
        print("Probando: get_wallet_transactions lanza excepción por error HTTP")
        mock_get.side_effect = Exception("Request failed")

        client = WalletExplorerClient()
        with self.assertRaises(Exception):
            client.get_wallet_transactions('wallet123')


if __name__ == '__main__':
    unittest.main()
