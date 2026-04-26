#include <iostream>

#include "myproject.h"
#include "parameters.h"

void myproject(
    hls::stream<input_t> &image_input,
    hls::stream<result_t> &layer29_out
) {

    // hls-fpga-machine-learning insert IO
    #pragma HLS INTERFACE axis port=image_input,layer29_out 
    // #pragma HLS DATAFLOW 

#ifndef __SYNTHESIS__
    static bool loaded_weights = false;
    if (!loaded_weights) {
        // hls-fpga-machine-learning insert load weights
        nnet::load_weights_from_txt<enc1_conv_weight_t, 144>(w2, "w2.txt");
        nnet::load_weights_from_txt<bias2_t, 16>(b2, "b2.txt");
        nnet::load_weights_from_txt<enc2_conv_weight_t, 2304>(w7, "w7.txt");
        nnet::load_weights_from_txt<bias7_t, 16>(b7, "b7.txt");
        nnet::load_weights_from_txt<bottleneck_conv_weight_t, 2304>(w12, "w12.txt");
        nnet::load_weights_from_txt<bias12_t, 16>(b12, "b12.txt");
        nnet::load_weights_from_txt<dec1_conv_weight_t, 2304>(w18, "w18.txt");
        nnet::load_weights_from_txt<bias18_t, 16>(b18, "b18.txt");
        nnet::load_weights_from_txt<dec2_conv_weight_t, 2304>(w24, "w24.txt");
        nnet::load_weights_from_txt<bias24_t, 16>(b24, "b24.txt");
        nnet::load_weights_from_txt<output_weight_t, 16>(w37, "w37.txt");
        nnet::load_weights_from_txt<output_bias_t, 1>(b37, "b37.txt");
        loaded_weights = true;
    }
#endif

    // ****************************************
    // NETWORK INSTANTIATION
    // ****************************************

    // hls-fpga-machine-learning insert layers

    hls::stream<layer32_t> layer32_out("layer32_out");
    #pragma HLS STREAM variable=layer32_out depth=1156
    nnet::zeropad2d_cl<input_t, layer32_t, config32>(image_input, layer32_out); // zp2d_enc1_conv

    hls::stream<layer2_t> layer2_out("layer2_out");
    #pragma HLS STREAM variable=layer2_out depth=1024
    nnet::conv_2d_cl<layer32_t, layer2_t, config2>(layer32_out, layer2_out, w2, b2); // enc1_conv

    hls::stream<layer5_t> layer5_out("layer5_out");
    #pragma HLS STREAM variable=layer5_out depth=1024
    nnet::relu<layer2_t, layer5_t, relu_config5>(layer2_out, layer5_out); // enc1_relu

    hls::stream<layer30_t> layer30_cpy1("layer30_cpy1");
    #pragma HLS STREAM variable=layer30_cpy1 depth=1024
    hls::stream<layer30_t> layer30_cpy2("layer30_cpy2");
    #pragma HLS STREAM variable=layer30_cpy2 depth=1024
    nnet::clone_stream<layer5_t, layer30_t, 16384>(layer5_out, layer30_cpy1, layer30_cpy2); // clone_enc1_relu

    hls::stream<layer6_t> layer6_out("layer6_out");
    #pragma HLS STREAM variable=layer6_out depth=256
    nnet::pooling2d_cl<layer30_t, layer6_t, config6>(layer30_cpy1, layer6_out); // max_pooling2d

    hls::stream<layer33_t> layer33_out("layer33_out");
    #pragma HLS STREAM variable=layer33_out depth=324
    nnet::zeropad2d_cl<layer6_t, layer33_t, config33>(layer6_out, layer33_out); // zp2d_enc2_conv

    hls::stream<layer7_t> layer7_out("layer7_out");
    #pragma HLS STREAM variable=layer7_out depth=256
    nnet::conv_2d_cl<layer33_t, layer7_t, config7>(layer33_out, layer7_out, w7, b7); // enc2_conv

    hls::stream<layer10_t> layer10_out("layer10_out");
    #pragma HLS STREAM variable=layer10_out depth=256
    nnet::relu<layer7_t, layer10_t, relu_config10>(layer7_out, layer10_out); // enc2_relu

    hls::stream<layer31_t> layer31_cpy1("layer31_cpy1");
    #pragma HLS STREAM variable=layer31_cpy1 depth=256
    hls::stream<layer31_t> layer31_cpy2("layer31_cpy2");
    #pragma HLS STREAM variable=layer31_cpy2 depth=256
    nnet::clone_stream<layer10_t, layer31_t, 4096>(layer10_out, layer31_cpy1, layer31_cpy2); // clone_enc2_relu

    hls::stream<layer11_t> layer11_out("layer11_out");
    #pragma HLS STREAM variable=layer11_out depth=64
    nnet::pooling2d_cl<layer31_t, layer11_t, config11>(layer31_cpy1, layer11_out); // max_pooling2d_1

    hls::stream<layer34_t> layer34_out("layer34_out");
    #pragma HLS STREAM variable=layer34_out depth=100
    nnet::zeropad2d_cl<layer11_t, layer34_t, config34>(layer11_out, layer34_out); // zp2d_bottleneck_conv

    hls::stream<layer12_t> layer12_out("layer12_out");
    #pragma HLS STREAM variable=layer12_out depth=64
    nnet::conv_2d_cl<layer34_t, layer12_t, config12>(layer34_out, layer12_out, w12, b12); // bottleneck_conv

    hls::stream<layer15_t> layer15_out("layer15_out");
    #pragma HLS STREAM variable=layer15_out depth=64
    nnet::relu<layer12_t, layer15_t, relu_config15>(layer12_out, layer15_out); // bottleneck_relu

    hls::stream<layer16_t> layer16_out("layer16_out");
    #pragma HLS STREAM variable=layer16_out depth=256
    nnet::resize_nearest<layer15_t, config16>(layer15_out, layer16_out); // up_sampling2d

    hls::stream<layer17_t> layer17_out("layer17_out");
    #pragma HLS STREAM variable=layer17_out depth=256
    nnet::add<layer16_t, layer31_t, layer17_t, config17>(layer16_out, layer31_cpy2, layer17_out); // skip_add_1

    hls::stream<layer35_t> layer35_out("layer35_out");
    #pragma HLS STREAM variable=layer35_out depth=324
    nnet::zeropad2d_cl<layer17_t, layer35_t, config35>(layer17_out, layer35_out); // zp2d_dec1_conv

    hls::stream<layer18_t> layer18_out("layer18_out");
    #pragma HLS STREAM variable=layer18_out depth=256
    nnet::conv_2d_cl<layer35_t, layer18_t, config18>(layer35_out, layer18_out, w18, b18); // dec1_conv

    hls::stream<layer21_t> layer21_out("layer21_out");
    #pragma HLS STREAM variable=layer21_out depth=256
    nnet::relu<layer18_t, layer21_t, relu_config21>(layer18_out, layer21_out); // dec1_relu

    hls::stream<layer22_t> layer22_out("layer22_out");
    #pragma HLS STREAM variable=layer22_out depth=1024
    nnet::resize_nearest<layer21_t, config22>(layer21_out, layer22_out); // up_sampling2d_1

    hls::stream<layer23_t> layer23_out("layer23_out");
    #pragma HLS STREAM variable=layer23_out depth=1024
    nnet::add<layer22_t, layer30_t, layer23_t, config23>(layer22_out, layer30_cpy2, layer23_out); // skip_add_2

    hls::stream<layer36_t> layer36_out("layer36_out");
    #pragma HLS STREAM variable=layer36_out depth=1156
    nnet::zeropad2d_cl<layer23_t, layer36_t, config36>(layer23_out, layer36_out); // zp2d_dec2_conv

    hls::stream<layer24_t> layer24_out("layer24_out");
    #pragma HLS STREAM variable=layer24_out depth=1024
    nnet::conv_2d_cl<layer36_t, layer24_t, config24>(layer36_out, layer24_out, w24, b24); // dec2_conv

    hls::stream<layer27_t> layer27_out("layer27_out");
    #pragma HLS STREAM variable=layer27_out depth=1024
    nnet::relu<layer24_t, layer27_t, relu_config27>(layer24_out, layer27_out); // dec2_relu

    hls::stream<layer37_t> layer37_out("layer37_out");
    #pragma HLS STREAM variable=layer37_out depth=1024
    nnet::pointwise_conv_2d_cl<layer27_t, layer37_t, config37>(layer27_out, layer37_out, w37, b37); // output

    nnet::sigmoid<layer37_t, result_t, sigmoid_config29>(layer37_out, layer29_out); // output_sigmoid

}
