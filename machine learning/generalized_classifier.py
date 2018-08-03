#!/usr/bin/env python3
''' Initialize a new model, or optionally load a previous one. Hopefully.

This script goes along the blog post
"Building powerful image classification models using very little data"
from blog.keras.io.
It uses data that can be downloaded at:
https://www.kaggle.com/c/dogs-vs-cats/data
In our setup, we:
- created a data/ folder
- created train/ and validation/ subfolders inside data/
- created cats/ and dogs/ subfolders inside train/ and validation/
- put the cat pictures index 0-999 in data/train/cats
- put the cat pictures index 1000-1400 in data/validation/cats
- put the dogs pictures index 12500-13499 in data/train/dogs
- put the dog pictures index 13500-13900 in data/validation/dogs
So that we have 1000 training examples for each class, and 400 validation examples for each class.
In summary, this is our directory structure:
```
data/
    train/
        dogs/
            dog001.jpg
            dog002.jpg
            ...
        cats/
            cat001.jpg
            cat002.jpg
            ...
    validation/
        dogs/
            dog001.jpg
            dog002.jpg
            ...
        cats/
            cat001.jpg
            cat002.jpg
            ...
```
'''

from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential, load_model
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras import backend as K
import argparse
import sys
import os
import pickle

def subdirs_file_count(folder):
    cpt = sum([len(files) for r, d, files in os.walk(folder)])
    return cpt
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weights', type=str, help='.h5 weights to load')
    ap.add_argument('-w', '--output_weights', type=str, default='new_weights.h5',
                    help='Name of weights file to save. Must by .h5 (def: \
                    new_weights.h5)')
    ap.add_argument('-m', '--output_model', default='model.model',
                    help='Name of saved model (def: model.model)')
    ap.add_argument('-l', '--load', type=str, 
                    help='Keras model to load. Otherwise initialize a new \
                    model')
    ap.add_argument('-e', '--epochs', type=int, default=50,
                    help='Number of epochs to preform (def: 50)')
    ap.add_argument('-b', '--batch', type=int, default=8,
                    help='Batch size <what does this mean?> (def: 8)')
    ap.add_argument('-d', '--data', type=str, default='data',
                    help='Path to load data from (def: ./data)')
    
    args = ap.parse_args()
    
    # Report
    print('Run %d epochs with a batch size of %d' % (args.epochs, args.batch))
    print('Output model name: %s' % args.output_model)

    return args
def evaluations(model):
    from sklearn.metrics import confusion_matrix

    def plot_images(images, cls_true, cls_pred=None):
    assert len(images) == len(cls_true) == 9
    
    # Create figure with 3x3 sub-plots.
    fig, axes = plt.subplots(3, 3)
    fig.subplots_adjust(hspace=0.3, wspace=0.3)

    for i, ax in enumerate(axes.flat):
        # Plot image.
        ax.imshow(images[i].reshape(img_shape), cmap='binary')

        # Show true and predicted classes.
        if cls_pred is None:
            xlabel = "True: {0}".format(cls_true[i])
        else:
            xlabel = "True: {0}, Pred: {1}".format(cls_true[i], cls_pred[i])

        # Show the classes as the label on the x-axis.
        ax.set_xlabel(xlabel)
        
        # Remove ticks from the plot.
        ax.set_xticks([])
        ax.set_yticks([])
    
    # Ensure the plot is shown correctly with multiple plots
    # in a single Notebook cell.
    plt.show()

def main():
    args = parse_args()

    # dimensions of our images.
    img_width, img_height = 299, 299

    train_data_dir = os.path.join(args.data, 'train')
    validation_data_dir = os.path.join(args.data, 'validation')
    nb_train_samples = subdirs_file_count(train_data_dir)
    print('nb train samples: %d' %nb_train_samples)
    nb_validation_samples = subdirs_file_count(validation_data_dir)
    print('nb validation samples: %d' %nb_validation_samples)
    epochs = args.epochs
    batch_size = 8

    if K.image_data_format() == 'channels_first':
        input_shape = (3, img_width, img_height)
    else:
        input_shape = (img_width, img_height, 3)

    def initialize_model(input_shape):
        model = Sequential()
        model.add(Conv2D(32, (3, 3), input_shape=input_shape))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Conv2D(32, (3, 3)))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Conv2D(64, (3, 3)))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))

        model.add(Flatten())
        model.add(Dense(64))
        model.add(Activation('relu')) 
        model.add(Dropout(0.5)) # learning rate?
        model.add(Dense(1))
        model.add(Activation('sigmoid'))

        model.compile(loss='binary_crossentropy',
                    optimizer='rmsprop',
                    metrics=['accuracy'])

        # load previous weights, if applicable
        if args.weights:
            model.load_weights(args.weights)

        return model
    if args.load:
        model = load_model(args.load)
    else:
        model = initialize_model

    # this is the augmentation configuration we will use for training
    train_datagen = ImageDataGenerator(
        rotation_range=180,
        width_shift_range=0.2,
        height_shift_range=0.2,
        rescale=1. / 255,
        shear_range=0.2,
        zoom_range=0.2,
        vertical_flip=True,
        horizontal_flip=True)

    # this is the augmentation configuration we will use for testing:
    # only rescaling
    test_datagen = ImageDataGenerator(rescale=1. / 255)

    train_generator = train_datagen.flow_from_directory(
        train_data_dir,
        target_size=(img_width, img_height),
        batch_size=batch_size,
        class_mode='binary')

    validation_generator = test_datagen.flow_from_directory(
        validation_data_dir,
        target_size=(img_width, img_height),
        batch_size=batch_size,
        class_mode='binary')

    history = model.fit_generator(
        train_generator,
        steps_per_epoch=nb_train_samples // batch_size,
        epochs=epochs,
        validation_data=validation_generator,
        validation_steps=nb_validation_samples // batch_size)

    # Print basic evaluation metrics
    # loss, accuracy = model.evaluate(train_generator, validation_generator)
    # print("\nLoss: %.2f, Accuracy: %.2f%%" % (loss, accuracy*100))

    # Save the model to allow training to pick up where we left off
    # model.save_weights(args.output_weights)
    model.save(args.output_model)

    # save a historydict object
    # load with `pickle.load(open('pickle_object', 'rb'))`
    hname = os.path.splitext(args.output_model)[0] + '-train_history.pkl'
    with open(hname, 'wb') as file_pi:
        pickle.dump(history.history, file_pi)

if __name__ == '__main__':
    main()
