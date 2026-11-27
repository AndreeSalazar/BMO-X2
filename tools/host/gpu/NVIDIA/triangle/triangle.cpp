#include <vulkan/vulkan.h>

#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace {
constexpr uint32_t width = 480;
constexpr uint32_t height = 360;
constexpr uint32_t frames = 48;
constexpr VkDeviceSize bytes = width * height * 4;
constexpr VkFormat format = VK_FORMAT_R8G8B8A8_UNORM;

void check(VkResult result, const char* operation)
{
    if (result != VK_SUCCESS) {
        throw std::runtime_error(std::string(operation) + ": " + std::to_string(result));
    }
}

struct Renderer {
    VkInstance instance{};
    VkPhysicalDevice physical{};
    VkDevice device{};
    VkQueue queue{};
    VkImage image{};
    VkImageView view{};
    VkImage texture{};
    VkDeviceMemory texture_memory{}, upload_memory{};
    VkBuffer upload{};
    VkSampler sampler{};
    VkDescriptorSetLayout texture_layout{};
    VkDescriptorPool texture_pool{};
    std::array<VkImageView, 2> texture_views{};
    std::array<VkDescriptorSet, 2> texture_sets{};
    VkDeviceMemory image_memory{}, readback_memory{};
    VkBuffer readback{};
    VkPipelineLayout layout{};
    VkPipeline pipeline{};
    VkShaderModule vertex{}, fragment{};
    VkCommandPool pool{};
    VkCommandBuffer cmd{};
    VkFence fence{};
    void* pixels{};
    VkImageLayout current_layout = VK_IMAGE_LAYOUT_UNDEFINED;

    ~Renderer()
    {
        if (device) {
            vkDeviceWaitIdle(device);
            if (pixels) vkUnmapMemory(device, readback_memory);
            if (fence) vkDestroyFence(device, fence, nullptr);
            if (pool) vkDestroyCommandPool(device, pool, nullptr);
            if (pipeline) vkDestroyPipeline(device, pipeline, nullptr);
            if (layout) vkDestroyPipelineLayout(device, layout, nullptr);
            if (texture_pool) vkDestroyDescriptorPool(device, texture_pool, nullptr);
            if (texture_layout) vkDestroyDescriptorSetLayout(device, texture_layout, nullptr);
            if (sampler) vkDestroySampler(device, sampler, nullptr);
            for (auto handle : texture_views) {
                if (handle) vkDestroyImageView(device, handle, nullptr);
            }
            if (texture) vkDestroyImage(device, texture, nullptr);
            if (texture_memory) vkFreeMemory(device, texture_memory, nullptr);
            if (upload) vkDestroyBuffer(device, upload, nullptr);
            if (upload_memory) vkFreeMemory(device, upload_memory, nullptr);
            if (fragment) vkDestroyShaderModule(device, fragment, nullptr);
            if (vertex) vkDestroyShaderModule(device, vertex, nullptr);
            if (readback) vkDestroyBuffer(device, readback, nullptr);
            if (readback_memory) vkFreeMemory(device, readback_memory, nullptr);
            if (view) vkDestroyImageView(device, view, nullptr);
            if (image) vkDestroyImage(device, image, nullptr);
            if (image_memory) vkFreeMemory(device, image_memory, nullptr);
            vkDestroyDevice(device, nullptr);
        }
        if (instance) vkDestroyInstance(instance, nullptr);
    }

    void open()
    {
        VkApplicationInfo app{VK_STRUCTURE_TYPE_APPLICATION_INFO};
        app.pApplicationName = "BMO-X2 NVIDIA triangle reference";
        app.apiVersion = VK_API_VERSION_1_3;
        VkInstanceCreateInfo ci{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
        ci.pApplicationInfo = &app;
        const char* validation = "VK_LAYER_KHRONOS_validation";
        ci.enabledLayerCount = 1;
        ci.ppEnabledLayerNames = &validation;
        check(vkCreateInstance(&ci, nullptr, &instance), "vkCreateInstance");
        uint32_t count{};
        check(vkEnumeratePhysicalDevices(instance, &count, nullptr), "physical count");
        std::vector<VkPhysicalDevice> devices(count);
        check(vkEnumeratePhysicalDevices(instance, &count, devices.data()), "physical devices");
        for (auto candidate : devices) {
            VkPhysicalDeviceProperties properties;
            vkGetPhysicalDeviceProperties(candidate, &properties);
            if (properties.vendorID == 0x10de && properties.deviceID == 0x2504 &&
                properties.apiVersion >= VK_API_VERSION_1_3) {
                physical = candidate;
                std::printf("GPU=%s\nVendor=%04x Device=%04x Vulkan=%u.%u.%u\n", properties.deviceName,
                            properties.vendorID, properties.deviceID, VK_API_VERSION_MAJOR(properties.apiVersion),
                            VK_API_VERSION_MINOR(properties.apiVersion), VK_API_VERSION_PATCH(properties.apiVersion));
                break;
            }
        }
        if (!physical) throw std::runtime_error("RTX 3060 10de:2504 with Vulkan 1.3 is required");

        vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, nullptr);
        std::vector<VkQueueFamilyProperties> families(count);
        vkGetPhysicalDeviceQueueFamilyProperties(physical, &count, families.data());
        uint32_t family = 0;
        while (family < count && !(families[family].queueFlags & VK_QUEUE_GRAPHICS_BIT)) ++family;
        if (family == count) throw std::runtime_error("Missing graphics queue");
        VkPhysicalDeviceVulkan13Features features{VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES};
        features.dynamicRendering = VK_TRUE;
        float priority = 1;
        VkDeviceQueueCreateInfo queue_info{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
        queue_info.queueFamilyIndex = family;
        queue_info.queueCount = 1;
        queue_info.pQueuePriorities = &priority;
        VkDeviceCreateInfo create{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
        create.pNext = &features;
        create.queueCreateInfoCount = 1;
        create.pQueueCreateInfos = &queue_info;
        check(vkCreateDevice(physical, &create, nullptr, &device), "vkCreateDevice");
        vkGetDeviceQueue(device, family, 0, &queue);
        VkCommandPoolCreateInfo cp{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
        cp.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        cp.queueFamilyIndex = family;
        check(vkCreateCommandPool(device, &cp, nullptr, &pool), "vkCreateCommandPool");
        VkCommandBufferAllocateInfo alloc{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        alloc.commandPool = pool;
        alloc.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        alloc.commandBufferCount = 1;
        check(vkAllocateCommandBuffers(device, &alloc, &cmd), "vkAllocateCommandBuffers");
        VkFenceCreateInfo done{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
        check(vkCreateFence(device, &done, nullptr, &fence), "vkCreateFence");
    }

    VkDeviceMemory allocate(VkMemoryRequirements requirements, VkMemoryPropertyFlags wanted)
    {
        VkPhysicalDeviceMemoryProperties properties;
        vkGetPhysicalDeviceMemoryProperties(physical, &properties);
        for (uint32_t i = 0; i < properties.memoryTypeCount; ++i) {
            if ((requirements.memoryTypeBits & (1u << i)) &&
                (properties.memoryTypes[i].propertyFlags & wanted) == wanted) {
                VkMemoryAllocateInfo info{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
                info.allocationSize = requirements.size;
                info.memoryTypeIndex = i;
                VkDeviceMemory memory{};
                check(vkAllocateMemory(device, &info, nullptr, &memory), "vkAllocateMemory");
                return memory;
            }
        }
        throw std::runtime_error("Missing memory type");
    }

    void make_target()
    {
        VkImageCreateInfo target{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        target.imageType = VK_IMAGE_TYPE_2D;
        target.format = format;
        target.extent = {width, height, 1};
        target.mipLevels = target.arrayLayers = 1;
        target.samples = VK_SAMPLE_COUNT_1_BIT;
        target.tiling = VK_IMAGE_TILING_OPTIMAL;
        target.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
        check(vkCreateImage(device, &target, nullptr, &image), "vkCreateImage");
        VkMemoryRequirements requirements;
        vkGetImageMemoryRequirements(device, image, &requirements);
        image_memory = allocate(requirements, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkBindImageMemory(device, image, image_memory, 0), "vkBindImageMemory");
        VkImageViewCreateInfo image_view{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        image_view.image = image;
        image_view.viewType = VK_IMAGE_VIEW_TYPE_2D;
        image_view.format = format;
        image_view.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        check(vkCreateImageView(device, &image_view, nullptr, &view), "vkCreateImageView");
        VkBufferCreateInfo buffer{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        buffer.size = bytes;
        buffer.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        check(vkCreateBuffer(device, &buffer, nullptr, &readback), "vkCreateBuffer");
        vkGetBufferMemoryRequirements(device, readback, &requirements);
        readback_memory = allocate(requirements, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkBindBufferMemory(device, readback, readback_memory, 0), "vkBindBufferMemory");
        check(vkMapMemory(device, readback_memory, 0, bytes, 0, &pixels), "vkMapMemory");
    }

    VkShaderModule shader(const char* path)
    {
        std::ifstream file(path, std::ios::binary | std::ios::ate);
        auto length = file.tellg();
        if (!file || length <= 0 || length % 4 != 0 || length > 65536) {
            throw std::runtime_error(std::string("Invalid SPIR-V: ") + path);
        }
        std::vector<uint32_t> words(static_cast<size_t>(length) / 4);
        file.seekg(0);
        if (!file.read(reinterpret_cast<char*>(words.data()), length)) throw std::runtime_error("SPIR-V read failed");
        VkShaderModuleCreateInfo module{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
        module.codeSize = static_cast<size_t>(length);
        module.pCode = words.data();
        VkShaderModule output;
        check(vkCreateShaderModule(device, &module, nullptr, &output), "vkCreateShaderModule");
        return output;
    }

    void make_textures()
    {
        constexpr uint8_t texels[] = {
            255, 74, 55, 255, 68, 223, 127, 255, 37, 110, 255, 255, 237, 212, 64, 255,
            169, 67, 244, 255, 33, 202, 219, 255, 250, 143, 51, 255, 241, 234, 247, 255,
        };
        VkImageCreateInfo source{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
        source.imageType = VK_IMAGE_TYPE_2D;
        source.format = format;
        source.extent = {2, 2, 1};
        source.mipLevels = 1;
        source.arrayLayers = static_cast<uint32_t>(texture_views.size());
        source.samples = VK_SAMPLE_COUNT_1_BIT;
        source.tiling = VK_IMAGE_TILING_OPTIMAL;
        source.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
        check(vkCreateImage(device, &source, nullptr, &texture), "texture image");
        VkMemoryRequirements requirements;
        vkGetImageMemoryRequirements(device, texture, &requirements);
        texture_memory = allocate(requirements, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
        check(vkBindImageMemory(device, texture, texture_memory, 0), "bind texture image");

        VkBufferCreateInfo staging{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        staging.size = sizeof(texels);
        staging.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT;
        check(vkCreateBuffer(device, &staging, nullptr, &upload), "texture staging");
        vkGetBufferMemoryRequirements(device, upload, &requirements);
        upload_memory = allocate(requirements, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                                               VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        check(vkBindBufferMemory(device, upload, upload_memory, 0), "bind texture staging");
        void* mapping{};
        check(vkMapMemory(device, upload_memory, 0, sizeof(texels), 0, &mapping), "map texture staging");
        std::memcpy(mapping, texels, sizeof(texels));
        vkUnmapMemory(device, upload_memory);

        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        check(vkBeginCommandBuffer(cmd, &begin), "begin texture upload");
        VkImageMemoryBarrier transition{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
        transition.image = texture;
        transition.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, source.arrayLayers};
        transition.srcQueueFamilyIndex = transition.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        transition.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
        transition.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        transition.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT,
                             0, 0, nullptr, 0, nullptr, 1, &transition);
        VkBufferImageCopy copy{};
        copy.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, source.arrayLayers};
        copy.imageExtent = source.extent;
        vkCmdCopyBufferToImage(cmd, upload, texture, transition.newLayout, 1, &copy);
        transition.oldLayout = transition.newLayout;
        transition.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        transition.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        transition.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
                             0, 0, nullptr, 0, nullptr, 1, &transition);
        finish_commands();
        vkDestroyBuffer(device, upload, nullptr);
        upload = {};
        vkFreeMemory(device, upload_memory, nullptr);
        upload_memory = {};

        VkSamplerCreateInfo sample{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
        sample.magFilter = sample.minFilter = VK_FILTER_NEAREST;
        sample.addressModeU = sample.addressModeV = sample.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
        check(vkCreateSampler(device, &sample, nullptr, &sampler), "texture sampler");
        VkDescriptorSetLayoutBinding binding{0, VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                                             1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr};
        VkDescriptorSetLayoutCreateInfo descriptor{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        descriptor.bindingCount = 1;
        descriptor.pBindings = &binding;
        check(vkCreateDescriptorSetLayout(device, &descriptor, nullptr, &texture_layout), "texture layout");
        VkDescriptorPoolSize size{binding.descriptorType, source.arrayLayers};
        VkDescriptorPoolCreateInfo pool_info{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        pool_info.maxSets = source.arrayLayers;
        pool_info.poolSizeCount = 1;
        pool_info.pPoolSizes = &size;
        check(vkCreateDescriptorPool(device, &pool_info, nullptr, &texture_pool), "texture pool");
        const std::array layouts{texture_layout, texture_layout};
        VkDescriptorSetAllocateInfo sets{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        sets.descriptorPool = texture_pool;
        sets.descriptorSetCount = source.arrayLayers;
        sets.pSetLayouts = layouts.data();
        check(vkAllocateDescriptorSets(device, &sets, texture_sets.data()), "texture sets");
        for (uint32_t layer = 0; layer < source.arrayLayers; ++layer) {
            VkImageViewCreateInfo layer_view{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
            layer_view.image = texture;
            layer_view.viewType = VK_IMAGE_VIEW_TYPE_2D;
            layer_view.format = format;
            layer_view.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, layer, 1};
            check(vkCreateImageView(device, &layer_view, nullptr, &texture_views[layer]), "texture view");
            VkDescriptorImageInfo sampled{sampler, texture_views[layer], transition.newLayout};
            VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            write.dstSet = texture_sets[layer];
            write.descriptorCount = 1;
            write.descriptorType = binding.descriptorType;
            write.pImageInfo = &sampled;
            vkUpdateDescriptorSets(device, 1, &write, 0, nullptr);
        }
    }

    void make_pipeline(const char* vert, const char* frag)
    {
        vertex = shader(vert);
        fragment = shader(frag);
        VkPushConstantRange push{VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(float)};
        VkPipelineLayoutCreateInfo scheme{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        scheme.pushConstantRangeCount = 1;
        scheme.pPushConstantRanges = &push;
        if (texture_layout) {
            scheme.setLayoutCount = 1;
            scheme.pSetLayouts = &texture_layout;
        }
        check(vkCreatePipelineLayout(device, &scheme, nullptr, &layout), "vkCreatePipelineLayout");
        VkPipelineShaderStageCreateInfo shaders[2] = {
            {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, nullptr, 0, VK_SHADER_STAGE_VERTEX_BIT, vertex, "main"},
            {VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, nullptr, 0, VK_SHADER_STAGE_FRAGMENT_BIT, fragment, "main"}
        };
        VkPipelineVertexInputStateCreateInfo input{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
        VkPipelineInputAssemblyStateCreateInfo assembly{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
        assembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
        VkViewport viewport{0, 0, float(width), float(height), 0, 1};
        VkRect2D scissor{{0,0},{width,height}};
        VkPipelineViewportStateCreateInfo viewport_state{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};
        viewport_state.viewportCount = viewport_state.scissorCount = 1;
        viewport_state.pViewports = &viewport;
        viewport_state.pScissors = &scissor;
        VkPipelineRasterizationStateCreateInfo raster{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};
        raster.polygonMode = VK_POLYGON_MODE_FILL;
        raster.lineWidth = 1;
        VkPipelineMultisampleStateCreateInfo sample{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};
        sample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;
        VkPipelineColorBlendAttachmentState attachment{};
        attachment.colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT |
                                    VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT;
        VkPipelineColorBlendStateCreateInfo blend{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
        blend.attachmentCount = 1;
        blend.pAttachments = &attachment;
        VkPipelineRenderingCreateInfo rendering{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};
        rendering.colorAttachmentCount = 1;
        rendering.pColorAttachmentFormats = &format;
        VkGraphicsPipelineCreateInfo graphics{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};
        graphics.pNext = &rendering;
        graphics.stageCount = 2;
        graphics.pStages = shaders;
        graphics.pVertexInputState = &input;
        graphics.pInputAssemblyState = &assembly;
        graphics.pViewportState = &viewport_state;
        graphics.pRasterizationState = &raster;
        graphics.pMultisampleState = &sample;
        graphics.pColorBlendState = &blend;
        graphics.layout = layout;
        check(vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1, &graphics, nullptr, &pipeline), "graphics pipeline");
    }

    void image_barrier(VkImageLayout next, VkPipelineStageFlags from, VkAccessFlags source,
                       VkPipelineStageFlags to, VkAccessFlags destination)
    {
        VkImageMemoryBarrier barrier{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
        barrier.oldLayout = current_layout;
        barrier.newLayout = next;
        barrier.srcQueueFamilyIndex = barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
        barrier.srcAccessMask = source;
        barrier.dstAccessMask = destination;
        barrier.image = image;
        barrier.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT,0,1,0,1};
        vkCmdPipelineBarrier(cmd, from, to, 0, 0, nullptr, 0, nullptr, 1, &barrier);
        current_layout = next;
    }

    void finish_commands()
    {
        check(vkEndCommandBuffer(cmd), "vkEndCommandBuffer");
        VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
        submit.commandBufferCount = 1;
        submit.pCommandBuffers = &cmd;
        check(vkResetFences(device, 1, &fence), "vkResetFences");
        check(vkQueueSubmit(queue, 1, &submit, fence), "vkQueueSubmit");
        check(vkWaitForFences(device, 1, &fence, VK_TRUE, 5000000000ull), "vkWaitForFences");
    }

    void draw(float angle, size_t texture_slot, const std::filesystem::path& file)
    {
        if (!std::isfinite(angle)) throw std::runtime_error("Invalid frame angle");
        const VkDescriptorSet sampled = texture_layout ? texture_sets.at(texture_slot) : VK_NULL_HANDLE;
        check(vkResetCommandBuffer(cmd, 0), "vkResetCommandBuffer");
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        check(vkBeginCommandBuffer(cmd, &begin), "vkBeginCommandBuffer");
        const bool first = current_layout == VK_IMAGE_LAYOUT_UNDEFINED;
        image_barrier(VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL,
                      first ? VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT : VK_PIPELINE_STAGE_TRANSFER_BIT,
                      first ? 0 : VK_ACCESS_TRANSFER_READ_BIT,
                      VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT);
        VkRenderingAttachmentInfo colors{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};
        colors.imageView = view;
        colors.imageLayout = current_layout;
        colors.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
        colors.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        colors.clearValue.color = {{0.030f, 0.037f, 0.071f, 1.0f}};
        VkRenderingInfo info{VK_STRUCTURE_TYPE_RENDERING_INFO};
        info.renderArea = {{0,0},{width,height}};
        info.layerCount = info.colorAttachmentCount = 1;
        info.pColorAttachments = &colors;
        vkCmdBeginRendering(cmd, &info);
        vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
        if (sampled) {
            vkCmdBindDescriptorSets(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, layout,
                                    0, 1, &sampled, 0, nullptr);
        }
        vkCmdPushConstants(cmd, layout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(angle), &angle);
        vkCmdDraw(cmd, 3, 1, 0, 0);
        vkCmdEndRendering(cmd);
        image_barrier(VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
                      VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_ACCESS_TRANSFER_READ_BIT);
        VkBufferImageCopy copy{};
        copy.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT,0,0,1};
        copy.imageExtent = {width,height,1};
        vkCmdCopyImageToBuffer(cmd, image, current_layout, readback, 1, &copy);
        VkMemoryBarrier visible{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        visible.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        visible.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_HOST_BIT, 0,
                             1, &visible, 0, nullptr, 0, nullptr);
        finish_commands();
        std::ofstream frame(file, std::ios::binary);
        if (!frame.write(static_cast<const char*>(pixels), bytes)) throw std::runtime_error("Frame write failed");
    }
};
}

int main(int argc, char** argv)
{
    const bool textured = argc == 5 && std::string_view(argv[4]) == "textured";
    if (argc != 4 && !textured) {
        std::fprintf(stderr, "Usage: triangle vertex.spv fragment.spv output-directory [textured]\n");
        return EXIT_FAILURE;
    }
    try {
        Renderer app;
        app.open();
        app.make_target();
        if (textured) app.make_textures();
        app.make_pipeline(argv[1], argv[2]);
        std::filesystem::create_directories(argv[3]);
        const auto start = std::chrono::steady_clock::now();
        for (uint32_t frame = 0; frame < frames; ++frame) {
            std::array<char, 16> name{};
            std::snprintf(name.data(), name.size(), "%02u.rgba", frame);
            const auto angle = float(textured ? frame / 2 : frame) * (6.283185307f / (textured ? frames / 2 : frames));
            app.draw(angle, frame % 2, std::filesystem::path(argv[3]) / name.data());
        }
        std::printf("Frames=%u Width=%u Height=%u\n", frames, width, height);
        if (textured) std::printf("Pipelines=1 TextureUploads=1 UploadedBytes=32 TextureBinds=%u\n", frames);
        const double ms = std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - start).count();
        std::printf("MeanSubmitReadbackWriteMs=%.3f\n", ms / frames);
        return EXIT_SUCCESS;
    } catch (const std::exception& error) {
        std::fprintf(stderr, "%s\n", error.what());
        return EXIT_FAILURE;
    }
}
