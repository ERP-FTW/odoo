# mlr_pos_nowpayments

Lightning Rod Point of Sale Now Payments Module Readme

Overview
<br>This custom module for Odoo 16+ to add Nodeless.io as a payment method to the Point-of-Sale application. Nodeless.io acts as payment gateway/provider for Bitcoin on-chain and lightning transactions, and is queried by API calls from Odoo. Nodeless is added as a new electronic payment method to the POS and Nodeless account access is provided by API to Odoo. The payment method can be set to provide a web URL for the customer to pay on a nodeless.io portal site or lightning/on-chain invoice so they pay directly from their wallet. A created invoice for an order is printed on the bill receipt for scanning by customers on paper or the screen. A customer can choose to pay in Lightning or a traditional payment method. The POS Validate payment button will check the status of the invoice and mark the order as paid if the invoice is settled. The method will also check the status of the payment every minute and validate the payment if made. Conversion rate and invoiced satoshis are stored for each order.

Prerequisites (versions)
<br>Compatible with Odoo 16
<br>Postgres 14+
<br>BTCpay server connected to Lightning node

Installation (see this video for tutorial on Odoo module installation)
1. Download repository and place extracted folder in the Odoo addons folder.
2. Login to Odoo database to upgrade and enable developer mode under settings.
3. Under apps Update the App list.
4. Search for the module (MLR) and install.

Setup

1. In Odoo navigate to Point of Sale-> Configuration -> Payment Methods .
2. Click New to create a new record.
![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/8a2f8d72-9720-4b3b-afa0-a2674bae43f5)
4. Enter a Name for the Payment Method (Bitcoin is suggested), select the journal as Bank, and select Nodeless from the Use Electronic Payment Terminal section.
5. Login into Nodeless.io to be used and navigate to Account -> API. Create a key for use with Odoo.
6. From Nodeless server the following information and paste in the Odoo Payment Method record: the server base URL (https://nodeless.io), API key, and store ID.
![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/9c24bbdb-3713-4268-8412-5692167b7188)
7. Select the payment flow of either Payment Link or Direct Invoice. Payment link will create a URL for the customer to visit to pay with either Bitcoin on-chain or with lightning. Direct Invoice currently requires the shop to select either on-chain or lightning to present to the customer. It is possible to create Payment Methods with identical Nodeless access information but different payment flows that can be used side-by-side in the POS.
8. Set the minimum and maximum payment amount in fiat, the nodeless range is 1000 satoshis minimum to $1000 maximum, so determine a corresponding amount for your Odoo set currency.
9. Click Test Cryptopay Server Connection to verify the information is correct. If it is correct a green popup will affirm so, if it is incorrect a red popup will appear.
   ![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/6f7d9c78-cfe9-4096-83d1-dcbc53e76867)
10. Save the record.
11. In Configuration -> Payment Methods add the newly created method and save.

Operation
1. From the Point of Sale Dashboard open a New Session.
2. After creating an order navigate to the payment screen and select the created Payment Method. On the Payment Line click Send to generate the payment information.
   ![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/0184554f-b9af-4334-b11f-add516236a82)
4. The Payment Line will display the Checking Invoice Status count and have a button Show receipt to view the invoice QR code on the bill receipt. 
![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/58de2de6-75c8-43c4-9005-a3d72752b4c0)
6. The QR code can be presented to the customer on the screen or with a printed receipt. Click Ok to navigate back to the Payment Screen.
![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/6b48aa92-b8b4-49c4-8e1a-7493da17418d)
7. If the customer paid with Lightning click Validate to confirm and close the order, if the invoice is unpaid a message will alert the user and an alternative payment method can be used. If the customer wishes to use another payment method, exe out the payment line and use the other payment method.
![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/05ca17aa-19fa-4161-a968-38a8e17be661)
![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/bedceef5-ec32-475a-b2e0-9289d527ee17)

8. Lightning payment information, satoshi amount and conversion rate, will be stored on the payment model. To view after closing the session navigate to Orders-> Payments and open a specific record.
![image](https://github.com/ERP-FTW/mlr_pos_nodeless_payments/assets/124227412/495d061a-6f71-4a3f-a83d-4fec7384f336)

