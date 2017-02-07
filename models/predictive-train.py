import os, time
os.environ['TF_CPP_MIN_LOG_LEVEL']='3'
import tensorflow as tf
import pandas
import argparse


CSV_LOCATION = 'games'
BATCH_SIZE = 100



def dir_location(name):
    i = 0
    while(os.path.isdir(name + '-v' + str(i))):    
        i += 1
    new_dir = name + '-v' + str(i)
    final_path = os.path.abspath(os.getcwd() + '\\' + new_dir)
    os.mkdir(final_path)
    return final_path


# class move_from_wrapper(object):
#     def __init__(self, sess):
#         self.sess = sess



# for now, just use full board state and predict piece chosen
def train_move_from(data, owner, labels, iterations):
    with tf.name_scope('input'):
        board_t = tf.placeholder(tf.float32, [None, 36])
        owner_t = tf.placeholder(tf.float32, [None, 36])
        move_taken_t = tf.placeholder(tf.float32, [None, 36])
        shaped_board = tf.reshape(board_t, [-1,6,6])
        shaped_owner = tf.reshape(owner_t, [-1,6,6])
        shaped_state = tf.stack([shaped_board, shaped_owner], axis=-1)

    with tf.name_scope('layer_1'):
        W_conv1 = weight_variable([4, 4, 2, 32])
        b_conv1 = bias_variable([32])

        h_conv1 = tf.nn.relu(conv2d(shaped_state, W_conv1) + b_conv1)
        # h_pool1 = max_pool_2x2(h_conv1)

    with tf.name_scope('layer_2'):
        W_conv2 = weight_variable([4, 4, 32, 64])
        b_conv2 = bias_variable([64])
        h_conv2 = tf.nn.relu(conv2d(h_conv1, W_conv2) + b_conv2)
        # h_pool2 = max_pool_2x2(h_conv2)

    with tf.name_scope('connected_layer_1'):
        W_fc1 = weight_variable([6*6*64, 1024])
        b_fc1 = bias_variable([1024])
        h_conv2_flat = tf.reshape(h_conv2, [-1, 6*6*64])
        h_fc1 = tf.nn.relu(tf.matmul(h_conv2_flat, W_fc1) + b_fc1)

    # with tf.name_scope('connected_layer_2'):
    #     W_fc2 = weight_variable([1024, 1024])
    #     b_fc2 = bias_variable([1024])
    #     h_fc2 = tf.nn.relu(tf.matmul(h_fc1, W_fc2) + b_fc2)

    with tf.name_scope('dropout'):
        keep_prob = tf.placeholder(tf.float32)
        tf.summary.scalar('dropout_keep_probability', keep_prob)
        h_fc2_drop = tf.nn.dropout(h_fc1, keep_prob)

    with tf.name_scope('readout'):
        W_fc2 = weight_variable([1024, 36])
        b_fc2 = bias_variable([36])

        y_conv = tf.matmul(h_fc2_drop, W_fc2) + b_fc2

    cross_entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=y_conv, labels=move_taken_t))
    train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy)
    correct_prediction = tf.equal(tf.argmax(y_conv, 1), tf.argmax(move_taken_t, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    saver = tf.train.Saver()

    print([v.name for v in tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)])
    exit()
    
    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())

        samples = len(data)
        loc = 0
        for i in range(iterations):
            batch = data[loc:loc+BATCH_SIZE]
            batch_labels = labels[loc:loc+BATCH_SIZE]
            batch_owner = owner[loc:loc+BATCH_SIZE]
            loc = (loc + BATCH_SIZE) % samples
            if (i-1) % 1000 == 0 or i < 10:
                train_accuracy = accuracy.eval(feed_dict={
                    owner_t: batch_owner, board_t: batch, move_taken_t: batch_labels, keep_prob: 1.0})
                print("step %d, training accuracy %g" % (i, train_accuracy))

            train_step.run(feed_dict={owner_t: batch_owner, board_t: batch, move_taken_t: batch_labels, keep_prob: 0.5})

        model_name = 'move_from'
        dir_save = dir_location(model_name)
        saver.save(sess, dir_save + '\\' + model_name)
        print('Saved move_to model to:', dir_save)

def train_move_to(data, owner, labels_from, labels_to, iterations):
    with tf.name_scope('input'):
        full_state_t = tf.placeholder(tf.float32, [None, 36])
        move_to_t = tf.placeholder(tf.float32, [None, 36])
        owner_t = tf.placeholder(tf.float32, [None, 36])
        move_from_t = tf.placeholder(tf.float32, [None, 36])
        shaped_state = tf.reshape(tf.stack([full_state_t, move_from_t, owner_t], axis=2), [-1, 6, 6, 3]) # 6x6, 3 channel

    with tf.name_scope('layer_1'):
        W_conv1 = weight_variable([4, 4, 3, 32]) # 4x4, 3 channel input, 32 channel output of 6x6es
        b_conv1 = bias_variable([32])

        h_conv1 = tf.nn.relu(conv2d(shaped_state, W_conv1) + b_conv1)

    with tf.name_scope('layer_2'):
        W_conv2 = weight_variable([4, 4, 32, 64])
        b_conv2 = bias_variable([64])
        h_conv2 = tf.nn.relu(conv2d(h_conv1, W_conv2) + b_conv2)

    with tf.name_scope('connected_layer'):
        W_fc1 = weight_variable([6*6*64, 1024])
        b_fc1 = bias_variable([1024])
        h_conv2_flat = tf.reshape(h_conv2, [-1, 6*6*64])
        h_fc1 = tf.nn.relu(tf.matmul(h_conv2_flat, W_fc1) + b_fc1)

    with tf.name_scope('dropout'):
        keep_prob = tf.placeholder(tf.float32)
        tf.summary.scalar('dropout_keep_probability', keep_prob)
        h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)

    with tf.name_scope('readout'):
        W_fc2 = weight_variable([1024, 36])
        b_fc2 = bias_variable([36])

        y_conv = tf.matmul(h_fc1_drop, W_fc2) + b_fc2

    cross_entropy = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=y_conv, labels=move_to_t))
    train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy)
    correct_prediction = tf.equal(tf.argmax(y_conv, 1), tf.argmax(move_to_t, 1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

    saver = tf.train.Saver()
    
    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())

        samples = len(board)
        loc = 0
        for i in range(iterations):
            batch = data[loc:loc+BATCH_SIZE]
            batch_labels = labels_from[loc:loc+BATCH_SIZE]
            batch_labels_to = labels_to[loc:loc+BATCH_SIZE]
            batch_owner = owner[loc:loc+BATCH_SIZE]

            loc = (loc + BATCH_SIZE) % samples
            if (i-1) % 1000 == 0 or i < 10:
                train_accuracy = accuracy.eval(feed_dict={
                    owner_t: batch_owner, full_state_t: batch, move_from_t: batch_labels, move_to_t: batch_labels_to, keep_prob: 1.0})
                print("step %d, training accuracy %g" % (i, train_accuracy))

            train_step.run(feed_dict={owner_t: batch_owner, full_state_t: batch, move_from_t: batch_labels, move_to_t: batch_labels_to, keep_prob: 0.5})


        model_name = 'move_to'
        dir_save = dir_location(model_name)
        saver.save(sess, dir_save + '\\' + model_name)
        print('Saved move_to model to:', dir_save)



def weight_variable(shape):
    """Create a weight variable with appropriate initialization."""
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial)

def bias_variable(shape):
    """Create a bias variable with appropriate initialization."""
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)

def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

def max_pool_2x2(x):
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1],
                          strides=[1, 2, 2, 1], padding='SAME')


def import_data():
    return pandas.read_pickle(CSV_LOCATION)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('model')
    parser.add_argument('iterations', default='10000')
    args = parser.parse_args()

    data = import_data()
    board = [item for sublist in data[['board']].as_matrix() for item in sublist]
    owner = [item for sublist in data[['owner']].as_matrix() for item in sublist]
    moves = data[['move_from']]
    labels_from = []
    for move in moves.as_matrix():
        temp = [0]*36
        temp[move[0]] = 1
        labels_from.append(temp)

    moves_to = data[['move_to']]
    labels_to = []
    for move in moves_to.as_matrix():
        temp = [0]*36
        temp[move[0]] = 1
        labels_to.append(temp)

    if args.model == 'from':
        train_move_from(board, owner, labels_from, int(args.iterations))
    if args.model == 'to':
        train_move_to(board, owner, labels_from, labels_to, int(args.iterations))