import torch
import torch.nn as nn
import numpy as np
from torchvision import transforms
import pdb
import matplotlib.pyplot as plt
import math
import torch.nn.functional as F
from kornia.geometry.transform import ScalePyramid, build_pyramid, resize
import kornia.geometry.transform as T


global feature_maps
feature_maps =  {'Net': 3,
                "resnet18_lacunarity": 512,
                "densenet_121": 3,
                "convnext": 3}


class Base_Lacunarity(nn.Module):
    def __init__(self, model_name = 'Net', dim=2, eps = 10E-6, scales = None, kernel = None, stride = None, padding = None, bias = False):


        # inherit nn.module
        super(Base_Lacunarity, self).__init__()

        self.bias = bias
        # define layer properties
        self.dim = dim
        self.eps = eps
        self.kernel = kernel
        self.stride = stride
        self.padding = padding
        self.scales = scales
        self.normalize = nn.Tanh()
        
        
        if self.bias == False: #Non learnable parameters
            self.conv1x1 = nn.Conv2d(len(self.scales) * feature_maps[model_name], 3, kernel_size=1, groups = feature_maps[self.model_name], bias = False)
            self.conv1x1.weight.data = torch.ones(self.conv1x1.weight.shape)*1/len(self.scales)
            self.conv1x1.weight.requires_grad = False #Don't update weights
        else:
            self.conv1x1 = nn.Conv2d(len(self.scales) * feature_maps[model_name], feature_maps[model_name], kernel_size=1, groups = feature_maps[model_name])


        #For each data type, apply two 1x1 convolutions, 1) to learn bin center (bias)
        # and 2) to learn bin width
        # Time series/ signal Data
        if self.kernel is None:
            if self.dim == 1:
                self.gap_layer = nn.AdaptiveAvgPool1d(1)
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AdaptiveAvgPool2d(1)
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AdaptiveAvgPool3d(1)
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')
        else:
            if self.dim == 1:
                self.gap_layer = nn.AvgPool1d((kernel[0]), stride=stride[0], padding=(0))
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AvgPool2d((kernel[0], kernel[1]), stride=(stride[0], stride[1]), padding=(0, 0))
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AvgPool3d((kernel[0], kernel[1], kernel[2]), stride=(stride[0], stride[1], stride[2]), padding=(0, 0, 0))
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')

        
    def forward(self,x):
        #Compute squared tensor
        lacunarity_values = []
        x = ((self.normalize(x) + 1)/2)* 255
        for scale in self.scales:
            scaled_x = x * scale
            squared_x_tensor = scaled_x ** 2

            #Get number of samples
            n_pts = np.prod(np.asarray(scaled_x.shape[-2:]))
            if (self.kernel == None):
                n_pts = np.prod(np.asarray(scaled_x.shape[-2:]))

            #Compute numerator (n * sum of squared pixels) and denominator (squared sum of pixels)
            L_numerator = ((n_pts)**2) * (self.gap_layer(squared_x_tensor))
            L_denominator = (n_pts * self.gap_layer(scaled_x))**2

            #Lacunarity is L_numerator / L_denominator - 1
            L_r = (L_numerator / (L_denominator + self.eps)) - 1
            lambda_param = 0.5 #boxcox transformation
            y = (torch.pow(L_r.abs() + 1, lambda_param) - 1) / lambda_param

            lacunarity_values.append(y)
        result = torch.cat(lacunarity_values, dim=1)
        return result



class Pixel_Lacunarity(nn.Module):
    def __init__(self, dim=2, eps = 10E-6, model_name=None, scales = None, kernel = None, stride = None, padding = None, bias = False):

        # inherit nn.module
        super(Pixel_Lacunarity, self).__init__()

        self.bias = bias
        # define layer properties
        self.dim = dim
        self.eps = eps
        self.kernel = kernel
        self.stride = stride
        self.padding = padding
        self.scales = scales
        self.model_name = model_name
        self.normalize = nn.Tanh()
        

        if self.bias == False: #Non learnable parameters
            self.conv1x1 = nn.Conv2d(len(self.scales) * feature_maps[self.model_name], feature_maps[self.model_name], kernel_size=1, bias = False)
            self.conv1x1.weight.data = torch.ones(self.conv1x1.weight.shape)*1/len(self.scales)
            self.conv1x1.weight.requires_grad = False #Don't update weights
        else:
            self.conv1x1 = nn.Conv2d(len(self.scales) * feature_maps[self.model_name], feature_maps[self.model_name], kernel_size=1, groups = feature_maps[self.model_name])


        #For each data type, apply two 1x1 convolutions, 1) to learn bin center (bias)
        # and 2) to learn bin width
        # Time series/ signal Data
        if self.kernel is None:
            if self.dim == 1:
                self.gap_layer = nn.AdaptiveAvgPool1d(1)
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AdaptiveAvgPool2d(1)
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AdaptiveAvgPool3d(1)
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')
        else:
            if self.dim == 1:
                self.gap_layer = nn.AvgPool1d((kernel[0]), stride=stride[0], padding=(0))
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AvgPool2d((kernel[0], kernel[1]), stride=(stride[0], stride[1]), padding=(0, 0))
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AvgPool3d((kernel[0], kernel[1], kernel[2]), stride=(stride[0], stride[1], stride[2]), padding=(0, 0, 0))
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')

        
    def forward(self,x):
        #Compute squared tensor
        lacunarity_values = []
        x = ((self.normalize(x) + 1)/2)* 255
        for scale in self.scales:
            scaled_x = x * scale
            squared_x_tensor = scaled_x ** 2

            #Get number of samples
            n_pts = np.prod(np.asarray(scaled_x.shape[-2:]))
            if (self.kernel == None):
                n_pts = np.prod(np.asarray(scaled_x.shape[-2:]))

            #Compute numerator (n * sum of squared pixels) and denominator (squared sum of pixels)
            L_numerator = ((n_pts)**2) * (self.gap_layer(squared_x_tensor))
            L_denominator = (n_pts * self.gap_layer(scaled_x))**2

            #Lacunarity is L_numerator / L_denominator - 1
            L_r = (L_numerator / (L_denominator + self.eps)) - 1
            lambda_param = 0.5 #boxcox transformation
            y = (torch.pow(L_r.abs() + 1, lambda_param) - 1) / lambda_param

            lacunarity_values.append(y)
        result = torch.cat(lacunarity_values, dim=1)
        reduced_output = self.conv1x1(result)
        return reduced_output


class ScalePyramid_Lacunarity(nn.Module):
    def __init__(self, dim=2, eps = 10E-6, model_name = "Net", num_levels = None, sigma = None, min_size = None, kernel = None, stride = None, padding = None):


        # inherit nn.module
        super(ScalePyramid_Lacunarity, self).__init__()

        # define layer properties
        self.dim = dim
        self.eps = eps
        self.kernel = kernel
        self.stride = stride
        self.padding = padding
        self.num_levels = num_levels
        self.sigma = sigma
        self.min_size = min_size
        self.normalize = nn.Tanh()
        self.model_name = model_name
        self.conv1x1 = nn.Conv2d(9, feature_maps[self.model_name], kernel_size=1)
        self.scalePyramid = ScalePyramid(n_levels = self.num_levels, init_sigma = self.sigma, min_size = self.min_size)
        #For each data type, apply two 1x1 convolutions, 1) to learn bin center (bias)
        # and 2) to learn bin width
        # Time series/ signal Data
        if self.kernel is None:
            if self.dim == 1:
                self.gap_layer = nn.AdaptiveAvgPool1d(1)
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AdaptiveAvgPool2d(1)
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AdaptiveAvgPool3d(1)
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')
        else:
            if self.dim == 1:
                self.gap_layer = nn.AvgPool1d((kernel[0]), stride=stride[0], padding=(0))
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AvgPool2d((kernel[0], kernel[1]), stride=(stride[0], stride[1]), padding=(0, 0))
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AvgPool3d((kernel[0], kernel[1], kernel[2]), stride=(stride[0], stride[1], stride[2]), padding=(0, 0, 0))
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')
            
    def create_conv1x1(self, in_channels):
        # Get the number of channels from the input
        # Create a new nn.Conv2d instance with the correct in_channels
        conv1x1 = nn.Conv2d(in_channels*feature_maps[self.model_name], feature_maps[self.model_name], kernel_size=1, groups = feature_maps[self.model_name])
        return conv1x1
    
        
    def forward(self,x):
        #Compute squared tensor
        lacunarity_values = []
        x = ((self.normalize(x) + 1)/2)* 255
        pyr_images, x, y = self.scalePyramid(x)
        print(len(pyr_images))

        if self.conv1x1.in_channels != len(pyr_images):
            self.conv1x1 = self.create_conv1x1(len(pyr_images))

        for scaled_x in pyr_images:
            scaled_x = scaled_x[:, :, 0, :, :]
            squared_x_tensor = scaled_x ** 2

            #Get number of samples
            n_pts = np.prod(np.asarray(scaled_x.shape[-2:]))
            if (self.kernel == None):
                n_pts = np.prod(np.asarray(scaled_x.shape[-2:]))


            #Compute numerator (n * sum of squared pixels) and denominator (squared sum of pixels)
            L_numerator = ((n_pts)**2) * (self.gap_layer(squared_x_tensor))
            L_denominator = (n_pts * self.gap_layer(scaled_x))**2

            #Lacunarity is L_numerator / L_denominator - 1
            L_r = (L_numerator / (L_denominator + self.eps)) - 1
            lambda_param = 0.5 #boxcox transformation
            y = (torch.pow(L_r.abs() + 1, lambda_param) - 1) / lambda_param


            lacunarity_values.append(y)
            reference_size = lacunarity_values[0].shape[-2:]
            pyr_images_resized = [T.resize(img, size=reference_size, interpolation="bilinear") for img in lacunarity_values]
        result = torch.cat(pyr_images_resized, dim=1)

        reduced_output = self.conv1x1(result)
        return reduced_output



class BuildPyramid(nn.Module):
    def __init__(self, dim=2, eps = 10E-6, model_name='Net', num_levels = None, kernel = None, stride = None, padding = None):


        # inherit nn.module
        super(BuildPyramid, self).__init__()

        # define layer properties
        self.model_name = model_name
        self.dim = dim
        self.eps = eps
        self.kernel = kernel
        self.stride = stride
        self.padding = padding
        self.num_levels = num_levels
        self.normalize = nn.Tanh()
        self.conv1x1 = nn.Conv2d(feature_maps[self.model_name]*self.num_levels, feature_maps[self.model_name], kernel_size=1, groups = feature_maps[self.model_name])

        #For each data type, apply two 1x1 convolutions, 1) to learn bin center (bias)
        # and 2) to learn bin width
        # Time series/ signal Data
        if self.kernel is None:
            if self.dim == 1:
                self.gap_layer = nn.AdaptiveAvgPool1d(1)
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AdaptiveAvgPool2d(1)
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AdaptiveAvgPool3d(1)
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')
        else:
            if self.dim == 1:
                self.gap_layer = nn.AvgPool1d((kernel[0]), stride=stride[0], padding=(0))
            
            # Image Data
            elif self.dim == 2:
                self.gap_layer = nn.AvgPool2d((kernel[0], kernel[1]), stride=(stride[0], stride[1]), padding=(0, 0))
            
            # Spatial/Temporal or Volumetric Data
            elif self.dim == 3:
                self.gap_layer = nn.AvgPool3d((kernel[0], kernel[1], kernel[2]), stride=(stride[0], stride[1], stride[2]), padding=(0, 0, 0))
             
            else:
                raise RuntimeError('Invalid dimension for global lacunarity layer')

    def create_conv1x1(self, in_channels):
        # Create a new nn.Conv2d instance with the correct in_channels
        conv1x1 = nn.Conv2d(in_channels*feature_maps[self.model_name], feature_maps[self.model_name], kernel_size=1, groups=feature_maps[self.model_name])
        return conv1x1
    
    def forward(self,x):
        #Compute squared tensor
        lacunarity_values = []
        x = ((self.normalize(x) + 1)/2)* 255
        pyr_images = build_pyramid(x, max_level=self.num_levels)

        if self.conv1x1.in_channels != len(pyr_images):
            self.conv1x1 = self.create_conv1x1(len(pyr_images))


        for scaled_x in pyr_images:
            squared_x_tensor = scaled_x ** 2

            #Get number of samples
            n_pts = np.prod(np.asarray(scaled_x.shape[-2:]))

            #Compute numerator (n * sum of squared pixels) and denominator (squared sum of pixels)
            L_numerator = ((n_pts)**2) * (self.gap_layer(squared_x_tensor))
            L_denominator = (n_pts * self.gap_layer(scaled_x))**2

            #Lacunarity is L_numerator / L_denominator - 1
            L_r = (L_numerator / (L_denominator + self.eps)) - 1
            lambda_param = 0.5 #boxcox transformation
            y = (torch.pow(L_r.abs() + 1, lambda_param) - 1) / lambda_param


            lacunarity_values.append(y)
            reference_size = lacunarity_values[0].shape[-2:]
            pyr_images_resized = [T.resize(img, size=reference_size, interpolation="bilinear") for img in lacunarity_values]

        result = torch.cat(pyr_images_resized, dim=1)

        reduced_output = self.conv1x1(result)
        return reduced_output

class DBC(nn.Module):
    def __init__(self, r_values=3, model_name='Net', window_size=3, eps = 10E-6):
        super(DBC, self).__init__()
        self.window_size = window_size
        self.normalize = nn.Tanh()
        self.r_values = r_values
        self.num_output_channels = 3
        self.eps = eps
        self.conv1x1 = nn.Conv2d(len(self.r_values) * 3, self.num_output_channels, kernel_size=1, groups = 3)


    def forward(self, image):
        image = ((self.normalize(image) + 1)/2)* 255
        L_r_all = []

        # Perform operations independently for each window in the current channel
        for r in self.r_values:
            max_pool = nn.MaxPool2d(kernel_size=self.window_size, stride=1)
            max_pool_output = max_pool(image)
            min_pool_output = -max_pool(-image)

            nr = torch.ceil(max_pool_output / (r + self.eps)) - torch.ceil(min_pool_output / (r + self.eps)) - 1
            Mr = torch.sum(nr)
            Q_mr = nr / (self.window_size - r + 1)
            L_r = (Mr**2) * Q_mr / (Mr * Q_mr + self.eps)**2
            L_r = L_r.squeeze(-1).squeeze(-1)
            L_r_all.append(L_r)
        channel_L_r = torch.cat(L_r_all, dim=1)
        reduced_output = self.conv1x1(channel_L_r)

        return reduced_output

class GDCB(nn.Module):
    def __init__(self, window_sizes, num_output_channels=3, eps=10E-6):
        super(DBC, self).__init__()
        self.window_sizes = window_sizes  # List of window sizes for lacunarity calculation
        self.normalize = nn.Tanh()
        self.num_output_channels = num_output_channels
        self.eps = eps
        self.conv1x1 = nn.Conv2d(len(self.window_sizes), self.num_output_channels, kernel_size=1)

    def forward(self, image):
        image = ((self.normalize(image) + 1) / 2) * 255
        lacunarity_values = []

        for d in self.window_sizes:
            max_pool_output = F.max_pool2d(image, kernel_size=d, stride=1)
            mean = torch.mean(max_pool_output)
            variance = torch.var(max_pool_output)
            lacunarity = variance / (mean**2)
            lacunarity_values.append(lacunarity)

        channel_lacunarity = torch.cat(lacunarity_values, dim=1)
        reduced_output = self.conv1x1(channel_lacunarity)

        return reduced_output


# # Example usage
# # Assuming input is a tensor of shape [batch_size, channels, height, width]
# input = torch.randn(32, 3, 13, 13)  # Batch size is 32

# num_patch_sizes = 10  # Choose the number of patch sizes to consider

# # Initialize the LacunarityCalculator
# lacunarity_calculator = DBC()

# # Forward pass to calculate lacunarity values
# lacunarity_values = lacunarity_calculator(input)

# # Print or use the lacunarity values as needed
# print("Lacunarity Values:")
# print(lacunarity_values.shape)




