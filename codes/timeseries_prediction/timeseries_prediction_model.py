import os,numpy
import pandas as pd
import numpy as np
import matplotlib.pylab as plt
from keras import Sequential
from keras.layers import LSTM, Dense
from matplotlib.pylab import rcParams
from sklearn.preprocessing import MinMaxScaler
# from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import acf,pacf
from statsmodels.tsa.arima_model import ARIMA
from statsmodels.tsa.arima_model import ARMA
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import r2_score
from datetime import datetime,timedelta

import pywt
import statsmodels.api as sm

from sklearn import ensemble
from sklearn import svm
from sklearn import neighbors


# LSTM支持包
# from keras.models import Sequential
# from keras.layers import Dense
# from keras.layers import LSTM

# 预测函数封装样例
def predict(host, cpu_data, mem_data, result_length=30, model='baseline', MA_window=12, ES_factor=0.7, ES_trend_factor=0.5, EWMA_factor=0.6, RFR_tree_num=20, LSTM_term_num=1500, LSTM_neuron_num=5):
	feature = ['avgvalue','maxvalue','minvalue']
	columns_cpu = ['cpu_avg','cpu_max','cpu_min','cpu_avg_1','cpu_max_1','cpu_min_1','cpu_avg_2','cpu_max_2','cpu_min_2']
	columns_mem = ['mem_avg','mem_max','mem_min','mem_avg_1','mem_max_1','mem_min_1','mem_avg_2','mem_max_2','mem_min_2']
	result = pd.DataFrame()
	result = result.append({'hostname':host},ignore_index = True)

	columns_indices = 0
	for j in feature:
		timeseries = cpu_data[j]
		if model == 'baseline':
			predict_TS = baseline_model(timeseries, result_length)
			predictions = predict_TS.values
		elif model == 'MA':
			predict_TS = moving_average_model(timeseries, MA_window, result_length)
			predictions = predict_TS.values
		elif model == 'ES':
			predict_TS = exponential_smoothing_model(timeseries, ES_factor, result_length)
			predictions = predict_TS.values
		elif model == 'ES_Trend':
			predict_TS = exponential_smoothing_trend_adjustment_model(timeseries, ES_factor, ES_trend_factor, result_length)
			predictions = predict_TS.values
		elif model == 'EWMA':
			predict_TS = exponential_weight_moving_average_model(timeseries, EWMA_factor, result_length)
			predictions = predict_TS.values
		elif model == 'Wavelet':
			try:
				predict_TS = wavelet_ARMA_model(timeseries, result_length)
				predictions = predict_TS.values
			except:
				print('data can not be stationary')
		elif model == 'RFR':
			predict_TS = random_forest_regressor_model(timeseries, result_length, RFR_tree_num)
			predictions = predict_TS.tolist()
		elif model == 'SVR':
			predict_TS = surpport_vector_regressor_model(timeseries, result_length)
			predictions = predict_TS.tolist()
		elif model == 'KNN':
			predict_TS = k_neighbors_regressor_model(timeseries, result_length)
			predictions = predict_TS.tolist()
		elif model == 'LSTM':
			testlen = result_length
			# 把数据变得平稳
			raw_values = timeseries.values
			diff_values = difference(raw_values, 1)
			# 转换数据变成监督学习问题
			supervised = timeseries_to_supervised(diff_values, 1)
			supervised_values = supervised.values
			# 把数据分成训练数据集和测试数据集
			train, test = supervised_values[0:-testlen], supervised_values[-testlen:]
			# 缩放数据
			scaler, train_scaled, test_scaled = scale(train, test)
			# 拟合模型
			lstm_model = fit_lstm(train_scaled, 1, LSTM_term_num, LSTM_neuron_num)
			# 预测训练集
			train_reshaped = train_scaled[:, 0].reshape(len(train_scaled), 1, 1)
			lstm_model.predict(train_reshaped, batch_size=1)
			# 在测试数据集上的前向验证
			predictions = list()
			for i in range(len(test_scaled)):
				# 做出一步预测
				X, y = test_scaled[i, 0:-1], test_scaled[i, -1]
				yhat = forecast_lstm(lstm_model, 1, X)
				# 反向缩放
				yhat = invert_scale(scaler, X, yhat)
				# 反向转换差分化数据
				yhat = inverse_difference(raw_values, yhat, len(test_scaled)+1-i)
				# 存储预测值
				predictions.append(yhat)
		result[columns_cpu[columns_indices]] = predictions[-1:]
		result[columns_cpu[columns_indices+3]] = timeseries.iloc[[len(timeseries)-1]][0]
		result[columns_cpu[columns_indices+6]] = timeseries.iloc[[len(timeseries)-2]][0]
		columns_indices = columns_indices + 1

	columns_indices = 0
	for j in feature:
		timeseries = mem_data[j]
		if model == 'baseline':
			predict_TS = baseline_model(timeseries, result_length)
			predictions = predict_TS.values
		elif model == 'MA':
			predict_TS = moving_average_model(timeseries, MA_window, result_length)
			predictions = predict_TS.values
		elif model == 'ES':
			predict_TS = exponential_smoothing_model(timeseries, ES_factor, result_length)
			predictions = predict_TS.values
		elif model == 'ES_Trend':
			predict_TS = exponential_smoothing_trend_adjustment_model(timeseries, ES_factor, ES_trend_factor, result_length)
			predictions = predict_TS.values
		elif model == 'EWMA':
			predict_TS = exponential_weight_moving_average_model(timeseries, EWMA_factor, result_length)
			predictions = predict_TS.values
		elif model == 'Wavelet':
			try:
				predict_TS = wavelet_ARMA_model(timeseries, result_length)
				predictions = predict_TS.values
			except:
				print('data can not be stationary')
		elif model == 'RFR':
			predict_TS = random_forest_regressor_model(timeseries, result_length, RFR_tree_num)
			predictions = predict_TS.tolist()
		elif model == 'SVR':
			predict_TS = surpport_vector_regressor_model(timeseries, result_length)
			predictions = predict_TS.tolist()
		elif model == 'KNN':
			predict_TS = k_neighbors_regressor_model(timeseries, result_length)
			predictions = predict_TS.tolist()
		elif model == 'LSTM':
			testlen = result_length
			# 把数据变得平稳
			raw_values = timeseries.values
			diff_values = difference(raw_values, 1)
			# 转换数据变成监督学习问题
			supervised = timeseries_to_supervised(diff_values, 1)
			supervised_values = supervised.values
			# 把数据分成训练数据集和测试数据集
			train, test = supervised_values[0:-testlen], supervised_values[-testlen:]
			# 缩放数据
			scaler, train_scaled, test_scaled = scale(train, test)
			# 拟合模型
			lstm_model = fit_lstm(train_scaled, 1, LSTM_term_num, LSTM_neuron_num)
			# 预测训练集
			train_reshaped = train_scaled[:, 0].reshape(len(train_scaled), 1, 1)
			lstm_model.predict(train_reshaped, batch_size=1)
			# 在测试数据集上的前向验证
			predictions = list()
			for i in range(len(test_scaled)):
				# 做出一步预测
				X, y = test_scaled[i, 0:-1], test_scaled[i, -1]
				yhat = forecast_lstm(lstm_model, 1, X)
				# 反向缩放
				yhat = invert_scale(scaler, X, yhat)
				# 反向转换差分化数据
				yhat = inverse_difference(raw_values, yhat, len(test_scaled)+1-i)
				# 存储预测值
				predictions.append(yhat)
		result[columns_mem[columns_indices]] = predictions[-1:]
		result[columns_mem[columns_indices+3]] = timeseries.iloc[[len(timeseries)-1]][0]
		result[columns_mem[columns_indices+6]] = timeseries.iloc[[len(timeseries)-2]][0]
		columns_indices = columns_indices + 1
	return result
	

# 基线模型
def baseline_model(timeseries, result_length):
	baseline_TS = timeseries.copy(deep=True)
	baseline_TS[baseline_TS!=0] = 0.0
	baseline_TS[0] = timeseries[0]
	baseline_TS = add_predict_term_to_timeseries(baseline_TS, 0.0)
	for i in range(1, len(baseline_TS)):
		baseline_TS[i] = timeseries[i-1]
	return baseline_TS[-result_length:]

# 滑动平均模型
def moving_average_model(timeseries, required_window, result_length):
	timeseries = add_predict_term_to_timeseries(timeseries, 0.0)
	MA_TS = timeseries.rolling(window = required_window).mean()
	return MA_TS[-result_length:]

# 指数平滑模型
def exponential_smoothing_model(timeseries, smoothing_factor, result_length):
	ES_TS = timeseries.copy(deep=True)
	ES_TS[ES_TS!=0] = 0.0
	ES_TS[0] = timeseries[0]
	ES_TS = add_predict_term_to_timeseries(ES_TS, 0.0)
	for i in range(1,len(ES_TS)):
		ES_TS[i] = smoothing_factor*timeseries[i-1]+(1-smoothing_factor)*ES_TS[i-1]
	return ES_TS[-result_length:]

# 指数平滑趋势调整模型
def exponential_smoothing_trend_adjustment_model(timeseries, smoothing_factor, trend_factor, result_length):
    ES_TS = timeseries.copy(deep=True)
    ES_TS[ES_TS!=0] = 0.0
    ES_TS[0] = timeseries[0]
    ES_TS = add_predict_term_to_timeseries(ES_TS, 0.0)
    ES_Trend = ES_TS.copy(deep=True)
    ES_Final = ES_TS.copy(deep=True)
    for i in range(1, len(ES_TS)):
        ES_TS[i] = smoothing_factor*timeseries[i-1] + (1-smoothing_factor)*ES_TS[i-1]
        ES_Trend[i] = (1-trend_factor)*ES_Trend[i-1] + trend_factor*(ES_TS[i]-ES_TS[i-1])
        ES_Final[i] = ES_TS[i] + ES_Trend[i]
    return ES_Final[-result_length:]

# 指数加权移动平均模型
def exponential_weight_moving_average_model(timeseries, weight_factor, result_length):
	EWMA_TS = timeseries.copy(deep=True)
	EWMA_TS[EWMA_TS!=0] = 0.0
	EWMA_TS[0] = timeseries[0]
	EWMA_TS = add_predict_term_to_timeseries(EWMA_TS, 0.0)
	for i in range(1, len(EWMA_TS)):
		weight = weight_factor/(i+weight_factor-1)
		EWMA_TS[i] = weight*timeseries[i-1]+(1-weight)*EWMA_TS[i-1]
	return EWMA_TS[-result_length:]

# 小波变换分解+ARMA模型
def wavelet_ARMA_model(timeseries, result_length):
	timeseries = add_predict_term_to_timeseries(timeseries, 0.0)

	index_list = np.array(timeseries)[:-result_length]
	date_list1 = np.array(timeseries.index)[:-result_length]

	index_for_predict = np.array(timeseries)[-result_length:]
	date_list2 = np.array(timeseries.index)[-result_length:]

    #分解
	A2,D2,D1 = pywt.wavedec(index_list,'db4',mode='sym',level=2)
	coeff=[A2,D2,D1]

    # 对每层小波系数求解模型系数
	order_A2 = sm.tsa.arma_order_select_ic(A2,ic='aic')['aic_min_order']
	order_D2 = sm.tsa.arma_order_select_ic(D2,ic='aic')['aic_min_order']
	order_D1 = sm.tsa.arma_order_select_ic(D1,ic='aic')['aic_min_order']

    #对每层小波系数构建ARMA模型
	model_A2 = ARMA(A2,order=order_A2)
	model_D2 = ARMA(D2,order=order_D2)
	model_D1 = ARMA(D1,order=order_D1)

	results_A2 = model_A2.fit()
	results_D2 = model_D2.fit()
	results_D1 = model_D1.fit()

	A2_all,D2_all,D1_all = pywt.wavedec(np.array(timeseries),'db4',mode='sym',level=2)
	delta = [len(A2_all)-len(A2),len(D2_all)-len(D2),len(D1_all)-len(D1)]

	pA2 = model_A2.predict(params=results_A2.params,start=1,end=len(A2)+delta[0])
	pD2 = model_D2.predict(params=results_D2.params,start=1,end=len(D2)+delta[1])
	pD1 = model_D1.predict(params=results_D1.params,start=1,end=len(D1)+delta[2])

	coeff_new = [pA2,pD2,pD1]
	denoised_index = pywt.waverec(coeff_new,'db4')

	temp_data_wt = {'pre_value':denoised_index[-result_length:]}
	Wavelet_TS = pd.DataFrame(temp_data_wt,index=date_list2,columns=['pre_value'])

	return Wavelet_TS['pre_value']

# 随机森林回归模型
def random_forest_regressor_model(timeseries, result_length, tree_num):
	train_set,varify_set,predict_set = construct_mechine_learning_set(timeseries, result_length)
	RFR = ensemble.RandomForestRegressor(tree_num)
	RFR.fit(train_set,varify_set)
	RFR_TS = RFR.predict(predict_set)
	return RFR_TS

# 支持向量机回归模型
def surpport_vector_regressor_model(timeseries, result_length):
	train_set,varify_set,predict_set = construct_mechine_learning_set(timeseries, result_length)
	SVR = svm.SVR()
	SVR.fit(train_set,varify_set)
	SVR_TS = SVR.predict(predict_set)
	return SVR_TS

# KNN回归模型
def k_neighbors_regressor_model(timeseries, result_length):
	train_set,varify_set,predict_set = construct_mechine_learning_set(timeseries, result_length)
	KNN = neighbors.KNeighborsRegressor()
	KNN.fit(train_set,varify_set)
	KNN_TS = KNN.predict(predict_set)
	return KNN_TS

# LSTM模型训练
def fit_lstm(train, batch_size, nb_epoch, neurons):
    X, y = train[:, 0:-1], train[:, -1]
    X = X.reshape(X.shape[0], 1, X.shape[1])
    model = Sequential()
    model.add(LSTM(neurons, batch_input_shape=(batch_size, X.shape[1], X.shape[2]), stateful=True))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    for i in range(nb_epoch):
        model.fit(X, y, epochs=1, batch_size=batch_size, verbose=0, shuffle=False)
        model.reset_states()
    return model
 
# LSTM模型做出一步预测
def forecast_lstm(model, batch_size, X):
    X = X.reshape(1, 1, len(X))
    yhat = model.predict(X, batch_size=batch_size)
    return yhat[0,0]



###############################################################################################################
# 辅助函数
# 时间序列转监督学习
def timeseries_to_supervised(timeseries, lag = 1):
	df = pd.DataFrame(timeseries)
	columns = [df.shift(i) for i in range(1, lag+1)]
	columns.append(df)
	df = pd.concat(columns, axis=1)
	df.fillna(0, inplace=True)
	return df

# 构建机器学习训练集、验证集、测试集
def construct_mechine_learning_set(timeseries, predict_set_length):
	train_set = timeseries[:-predict_set_length]
	temp = timeseries_to_supervised(train_set, 1)
	train_set = np.array(train_set).reshape(-1,1)
	varify_set = temp.iloc[:,0]
	predict_set = np.array(timeseries[-predict_set_length:]).reshape(-1,1)
	return train_set,varify_set,predict_set

# 在时间序列末端插入一行
def add_predict_term_to_timeseries(timeseries, predict_value):
	last_term_date = timeseries.tail(1).index.tolist()
	new_term_date = last_term_date[0] + timedelta(hours = 1)
	new_term = pd.Series(predict_value, index = [new_term_date])
	timeseries = timeseries.append(new_term)
	return timeseries

# 差分
def difference(timeseries, interval=1):
    diff = list()
    for i in range(interval, len(timeseries)):
        value = timeseries[i] - timeseries[i - interval]
        diff.append(value)
    return pd.Series(diff)

# 反向差分
def inverse_difference(history, timeseries_result, interval=1):
    return timeseries_result + history[-interval]

# 缩放预测值到[0,1]
def scale(train, test):
    # fit scale
    scaler = MinMaxScaler(feature_range=(-1, 1))
    scaler = scaler.fit(train)
    # transform train
    train = train.reshape(train.shape[0], train.shape[1])
    train_scaled = scaler.transform(train)
    # transform test
    test = test.reshape(test.shape[0], test.shape[1])
    test_scaled = scaler.transform(test)
    return scaler, train_scaled, test_scaled
 
# 反缩放预测值
def invert_scale(scaler, X, value):
    new_row = [x for x in X] + [value]
    array = numpy.array(new_row)
    array = array.reshape(1, len(array))
    inverted = scaler.inverse_transform(array)
    return inverted[0, -1]