import tensorflow as tf
import numpy as np
import time, datetime
import os
# CIFAR-10 데이터를 다운로드 받기 위한 keras의 helper 함수인 load_data 함수를 임포트합니다.
from tensorflow.keras.datasets.cifar100 import load_data

N_EPISODES = 2000
batch_size = 100

DIR_Checkpoint  = "/tmp/ML/10_Cifar100_Tensorboard_Save_Restore/CheckPoint"
DIR_Tensorboard = "/tmp/ML/10_Cifar100_Tensorboard_Save_Restore/Tensorboard"

# 학습에 직접적으로 사용하지 않고 학습 횟수에 따라 단순히 증가시킬 변수를 만듭니다.
global_step = tf.Variable(0, trainable=False, name='global_step')

# 다음 배치를 읽어오기 위한 next_batch 유틸리티 함수를 정의합니다.
def next_batch(num, data, labels):
    '''
    `num` 개수 만큼의 랜덤한 샘플들과 레이블들을 리턴합니다.
    '''
    idx = np.arange(0 , len(data))
    np.random.shuffle(idx)
    idx = idx[:num]
    data_shuffle = [data[ i] for i in idx]
    labels_shuffle = [labels[ i] for i in idx]

    return np.asarray(data_shuffle), np.asarray(labels_shuffle)

# CNN 모델을 정의합니다. 
def BUILD_NETWORK_CNN(x):
    # 입력 이미지
    x_image = x
    

    with tf.name_scope('Conv_Layer_01'):
        # 첫번째 convolutional layer - 하나의 grayscale 이미지를 64개의 특징들(feature)으로 맵핑(maping)합니다.
        W_conv1 = tf.Variable(tf.truncated_normal(shape=[5, 5, 3, 64], stddev=5e-2))
        b_conv1 = tf.Variable(tf.constant(0.1, shape=[64]))
        h_conv1 = tf.nn.relu(tf.nn.conv2d(x_image, W_conv1, strides=[1, 1, 1, 1], padding='SAME') + b_conv1)
        
        tf.summary.histogram("x_image", x_image)
        tf.summary.histogram("Weights_01", W_conv1)
    
    with tf.name_scope('Pool_Layer_01'):
        # 첫번째 Pooling layer
        h_pool1 = tf.nn.max_pool(h_conv1, ksize=[1, 3, 3, 1], strides=[1, 2, 2, 1], padding='SAME')

    with tf.name_scope('Conv_Layer_02'):
        # 두번째 convolutional layer - 32개의 특징들(feature)을 64개의 특징들(feature)로 맵핑(maping)합니다.
        W_conv2 = tf.Variable(tf.truncated_normal(shape=[5, 5, 64, 64], stddev=5e-2))
        b_conv2 = tf.Variable(tf.constant(0.1, shape=[64]))
        h_conv2 = tf.nn.relu(tf.nn.conv2d(h_pool1, W_conv2, strides=[1, 1, 1, 1], padding='SAME') + b_conv2)
    
        tf.summary.histogram("Weights_02", W_conv2)
        
    with tf.name_scope('Pool_Layer_02'):
        # 두번째 pooling layer.
        h_pool2 = tf.nn.max_pool(h_conv2, ksize=[1, 3, 3, 1], strides=[1, 2, 2, 1], padding='SAME')

    with tf.name_scope('Conv_Layer_03'):
        # 세번째 convolutional layer
        W_conv3 = tf.Variable(tf.truncated_normal(shape=[3, 3, 64, 128], stddev=5e-2))
        b_conv3 = tf.Variable(tf.constant(0.1, shape=[128]))
        h_conv3 = tf.nn.relu(tf.nn.conv2d(h_pool2, W_conv3, strides=[1, 1, 1, 1], padding='SAME') + b_conv3)

        tf.summary.histogram("Weights_03", W_conv3)

    with tf.name_scope('Conv_Layer_04'):
        # 네번째 convolutional layer
        W_conv4 = tf.Variable(tf.truncated_normal(shape=[3, 3, 128, 128], stddev=5e-2))
        b_conv4 = tf.Variable(tf.constant(0.1, shape=[128])) 
        h_conv4 = tf.nn.relu(tf.nn.conv2d(h_conv3, W_conv4, strides=[1, 1, 1, 1], padding='SAME') + b_conv4)

        tf.summary.histogram("Weights_04", W_conv4)
        
    with tf.name_scope('Conv_Layer_05'):
        # 다섯번째 convolutional layer
        W_conv5 = tf.Variable(tf.truncated_normal(shape=[3, 3, 128, 128], stddev=5e-2))
        b_conv5 = tf.Variable(tf.constant(0.1, shape=[128]))
        h_conv5 = tf.nn.relu(tf.nn.conv2d(h_conv4, W_conv5, strides=[1, 1, 1, 1], padding='SAME') + b_conv5)

        tf.summary.histogram("Weights_05", W_conv5)
        
    with tf.name_scope('Dense_Layer_01'):
        # Fully Connected Layer 1 - 2번의 downsampling 이후에, 우리의 32x32 이미지는 8x8x128 특징맵(feature map)이 됩니다.
        # 이를 384개의 특징들로 맵핑(maping)합니다.
        W_fc1 = tf.Variable(tf.truncated_normal(shape=[8 * 8 * 128, 384], stddev=5e-2))
        b_fc1 = tf.Variable(tf.constant(0.1, shape=[384]))

        h_conv5_flat = tf.reshape(h_conv5, [-1, 8*8*128])
        h_fc1 = tf.nn.relu(tf.matmul(h_conv5_flat, W_fc1) + b_fc1)

        # Dropout - 모델의 복잡도를 컨트롤합니다. 특징들의 co-adaptation을 방지합니다.
        h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob) 

        tf.summary.histogram("Weights_06", W_fc1)
        
    with tf.name_scope('Output_Layer'):
        # Fully Connected Layer 2 - 384개의 특징들(feature)을 10개의 클래스-airplane, automobile, bird...-로 맵핑(maping)합니다.
        W_fc2 = tf.Variable(tf.truncated_normal(shape=[384, 100], stddev=5e-2))
        b_fc2 = tf.Variable(tf.constant(0.1, shape=[100]))
        logits = tf.matmul(h_fc1_drop,W_fc2) + b_fc2
        y_pred = tf.nn.softmax(logits)
        
        tf.summary.histogram("Weights_07", W_fc2)
        tf.summary.histogram("Prediction", y_pred)

    return y_pred, logits

# 인풋 아웃풋 데이터, 드롭아웃 확률을 입력받기위한 플레이스홀더를 정의합니다.
x = tf.placeholder(tf.float32, shape=[None, 32, 32, 3])
y = tf.placeholder(tf.float32, shape=[None, 100])
keep_prob = tf.placeholder(tf.float32)

# CIFAR-10 데이터를 다운로드하고 데이터를 불러옵니다.
(X_train, Y_train), (X_test, Y_test) = load_data()
# scalar 형태의 레이블(0~9)을 One-hot Encoding 형태로 변환합니다.
Y_train_one_hot = tf.squeeze(tf.one_hot(Y_train, 100),axis=1)
Y_test_one_hot = tf.squeeze(tf.one_hot(Y_test, 100),axis=1)

# Convolutional Neural Networks(CNN) 그래프를 생성합니다.
y_pred, logits = BUILD_NETWORK_CNN(x)

# Cross Entropy를 비용함수(loss function)으로 정의하고, RMSPropOptimizer를 이용해서 비용 함수를 최소화합니다.with tf.name_scope('optimizer'):

with tf.name_scope('Optimizer'):
    loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels=y, logits=logits))
    optimizer = tf.train.RMSPropOptimizer(1e-3).minimize(loss, global_step=global_step)
    
    # tf.summary.scalar 를 사용하여 기록해야할 tensor들을 수집, tensor들이 너무 많으면 시각화가 복잡하므로 간단한것만 선택.
    tf.summary.scalar('cost', loss)

# 정확도를 계산하는 연산을 추가합니다.
correct_prediction = tf.equal(tf.argmax(y_pred, 1), tf.argmax(y, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

# 세션을 열어 실제 학습을 진행합니다.
with tf.Session() as sess:
    init = tf.global_variables_initializer()
    # 모든 변수들을 초기화한다. 
    # sess.run(tf.global_variables_initializer())
    start_time = time.time()

    if not os.path.exists(DIR_Checkpoint):
        os.makedirs(DIR_Checkpoint)
    if not os.path.exists(DIR_Tensorboard):
        os.makedirs(DIR_Tensorboard)

    saver = tf.train.Saver(tf.global_variables())

    ckpt = tf.train.get_checkpoint_state(DIR_Checkpoint)

    if ckpt and tf.train.checkpoint_exists(ckpt.model_checkpoint_path):
        saver.restore(sess, ckpt.model_checkpoint_path)
        print('Variables are restored!')
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    else:
        sess.run(init)
        print('Variables are initialized!')
        print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    
    # 텐서보드에서 표시해주기 위한 텐서들을 수집합니다.
    merged = tf.summary.merge_all()
    # 저장할 그래프와 텐서값들을 저장할 디렉토리를 설정합니다.
    writer = tf.summary.FileWriter(DIR_Tensorboard, sess.graph)
    # 이렇게 저장한 로그는, 학습 후 다음의 명령어를 이용해 웹서버를 실행시킨 뒤
    # tensorboard --logdir=./logs
    # 다음 주소와 웹브라우저를 이용해 텐서보드에서 확인할 수 있습니다.
    # http://localhost:6006

    # train my model
    print('Learning started. It takes sometime.')

    # train my model
    Total_batch = int(X_train.shape[0]/batch_size) 
    # print("Size Train : ", X_train.shape[0])
    # print("Size Test  : ", X_test.shape[0])
    # print("Total batch : ", Total_batch)

    # 10000 Step만큼 최적화를 수행합니다.
    for episode in range(N_EPISODES):
        total_cost = 0
        for i in range(Total_batch):
            batch = next_batch(batch_size, X_train, Y_train_one_hot.eval())

            # 100 Step마다 training 데이터셋에 대한 정확도와 loss를 출력합니다.
            
            train_accuracy = accuracy.eval(feed_dict={x: batch[0], y: batch[1], keep_prob: 1.0})
            loss_print = loss.eval(feed_dict={x: batch[0], y: batch[1], keep_prob: 1.0})

                
            # 20% 확률의 Dropout을 이용해서 학습을 진행합니다.
            sess.run(optimizer, feed_dict={x: batch[0], y: batch[1], keep_prob: 0.8})
            total_cost += loss_print
        # print("Epoch: %6d, Loss: %2.6f" % (episode+1, total_cost/Total_batch))
        print('Global Step:', '%07d' % int(sess.run(global_step)/Total_batch), 'cost =', '{:02.6f}'.format(total_cost/Total_batch))
        
        elapsed_time = datetime.timedelta(seconds=int(time.time()-start_time))
        print("[{}]".format(elapsed_time))

        # 적절한 시점에 저장할 값들을 수집하고 저장합니다.
        summary = sess.run(merged, feed_dict={x: batch[0], y: batch[1], keep_prob: 0.8})
        writer.add_summary(summary, global_step=sess.run(global_step))

        # 최적화가 끝난 뒤, 변수를 저장합니다.
        #saver.save(sess, './model/dnn.ckpt', global_step=global_step)
        if (episode + 1) % 100 == 0 or episode == N_EPISODES:
            saver.save(sess, DIR_Checkpoint + './dnn.ckpt', global_step=global_step)
            
    print('Learning Finished!')
    
    # 학습이 끝나면 테스트 데이터(10000개)에 대한 정확도를 출력합니다.  
    test_accuracy = 0.0  
    for i in range(10):
        test_batch = next_batch(1000, X_test, Y_test_one_hot.eval())
        test_accuracy = test_accuracy + accuracy.eval(feed_dict={x: test_batch[0], y: test_batch[1], keep_prob: 1.0})
    test_accuracy = test_accuracy / 10;
    print("Test Data Accuracy: %2.4f" % test_accuracy)
    elapsed_time = time.time() - start_time
    formatted = datetime.timedelta(seconds=int(elapsed_time))
    print("=== training time elapsed: {}s ===".format(formatted))


