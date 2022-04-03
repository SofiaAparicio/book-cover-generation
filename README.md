# book-cover-generation

This project belongs to the [HugGAN Sprint](https://github.com/huggingface/community-events/tree/main/huggan), the main objetive is to build a model that generates book covers. 

## Phases of research

### Dataset construction
In this phase we will build the dataset to train the model, this dataset should have the book cover and also metadata about the book.
Being that, the objetive is to make it public available, one could use it to build other models with different objetives.


### Model training 
In order to generate the book cover we will use some of the metadata to generate this image, as such, we will use a text-to-image model.
However, being this area a hot topic in the research comunity there are alot of different approaches to solve this task.

#### Current approaches 
- Using VQ-VAE and Transformers to model the image.
  - https://github.com/cientgu/vq-diffusion
  - https://github.com/drboog/Lafite
  - https://github.com/ofa-sys/ofa