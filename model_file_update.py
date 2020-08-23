from wb_creds import wb_token_64
from wildberries import WBConnector, get_reporting_date_by_gap
import pandas as pd

orders = WBConnector(wb_token_64, 'orders')

reporting_date_for_fit = get_reporting_date_by_gap(85)
df_orders_fit = orders.get_data_df(reporting_date_for_fit)

df_orders_fit = df_orders_fit[['nmId', 'isCancel']]
df_orders_fit['isCancel'] = df_orders_fit['isCancel'].astype(float)
df_orders_fit = df_orders_fit.groupby('nmId', as_index=False).mean()
df_orders_fit['SaleRate'] = 1 - df_orders_fit['isCancel']
df_orders_fit = df_orders_fit[['nmId', 'SaleRate']]
df_orders_fit.to_csv('Sales_model_.csv', index=False, encoding='utf-8-sig')
