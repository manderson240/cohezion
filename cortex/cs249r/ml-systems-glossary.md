---
tags: [glossary, ml-systems, cs249r]
source: cs249r/global_glossary
date: 2026-02-18
term_count: 656
aspect: knower
neural:
  activation: 1.0
  stage: growing
  synapse_in: 1
  synapse_out: 8
---

# ML Systems Glossary

**Source:** CS249R ML Systems Book - Global Glossary
**Terms:** 656

## 3

**3dmark**: Graphics performance benchmark suite that evaluates real-time 3D rendering capabilities, measuring triangle throughput, texture fill rates, and modern features like ray tracing and DLSS performance.

## A

**a/b testing**: A controlled experimental method for comparing two versions of a system or model by randomly dividing users into groups and measuring performance differences between the variants

**accountability**: The mechanisms by which individuals or organizations are held responsible for the outcomes of AI systems, involving traceability, documentation, auditing, and the ability to remedy harms.

**activation checkpointing**: A memory optimization technique that reduces memory usage during backpropagation by selectively discarding and recomputing activations instead of storing all intermediate results.

**activation function**: A mathematical function applied to the weighted sum of inputs in a neural network neuron to introduce nonlinearity, enabling the network to learn complex patterns beyond simple linear combinations.

**activation-based pruning**: A pruning method that evaluates the average activation values of neurons or filters over a dataset to identify and remove neurons that consistently produce low activations and contribute little information to the network's decision process.

**active learning**: Iteratively selecting the most informative samples for labeling to maximize learning efficiency, achieving target performance with 50-90% less labeled data compared to random sampling strategies

**adam optimization**: An adaptive learning rate optimization algorithm that combines momentum and RMSprop by maintaining exponentially decaying averages of both gradients and squared gradients for each parameter.

**adapter modules**: Small trainable neural network components inserted between frozen layers of a pretrained model to enable lightweight adaptation without modifying the base architecture.

**adaptive resource pattern**: A design pattern that enables systems to dynamically adjust their operations in response to varying resource availability, ensuring efficiency and resilience by scaling up or down based on computational load, network bandwidth, and storage capacity.

**adversarial attack**: A type of attack where carefully crafted inputs are designed to cause machine learning models to make incorrect predictions while remaining nearly indistinguishable from legitimate data to humans

**adversarial example**: A maliciously modified input that is designed to fool a machine learning model into making an incorrect prediction, often created by adding small, imperceptible perturbations to legitimate data

**adversarial training**: A defense technique that involves training models on adversarial examples to improve their robustness and ability to correctly classify adversarial inputs

**agi**: Artificial General Intelligence - computational systems that match or exceed human cognitive capabilities across all domains of knowledge and reasoning, capable of generalizing across diverse problem domains without task-specific training.

**ai for good**: The design, development, and deployment of machine learning systems aimed at addressing important societal and environmental challenges to enhance human welfare, promote sustainability, and contribute to global development goals.

**alerting**: Automated notification systems that inform teams when metrics exceed predefined thresholds or anomalies are detected in production ML systems.

**alexnet**: A groundbreaking convolutional neural network architecture that won the 2012 ImageNet challenge, reducing error rates from 26% to 16% and sparking the deep learning renaissance.

**algorithmic efficiency**: The design and optimization of algorithms to maximize performance within given resource constraints, focusing on techniques like model compression, architectural optimization, and algorithmic refinement.

**algorithmic fairness**: The principle that automated systems should not disproportionately disadvantage individuals or groups based on protected attributes such as race, gender, or age.

**all-reduce**: A collective communication operation in distributed computing where each process contributes data and all processes receive the combined result, commonly used for gradient aggregation in distributed training.

**alphafold**: A landmark AI system developed by DeepMind that predicts the three-dimensional structure of proteins from their amino acid sequences, solving the decades-old "protein folding problem" and demonstrating how large-scale ML systems can accelerate scientific discovery.

**anomaly detection**: The identification of patterns in data that do not conform to expected behavior, often used to detect outliers, faults, or malicious activities in systems.

**anonymization**: The process of removing or modifying personally identifiable information from datasets to protect individual privacy, though often insufficient against sophisticated re-identification attacks.

**apache kafka**: A distributed streaming platform that handles real-time data feeds using a publish-subscribe messaging system, commonly used for building ML data pipelines with high throughput and fault tolerance.

**apache spark**: An open-source distributed computing framework that enables large-scale data processing across clusters of computers, revolutionizing ETL operations with in-memory computing capabilities.

**application-specific integrated circuit**: A specialized chip designed for specific tasks that offers maximum efficiency by abandoning general-purpose flexibility, exemplified by Cerebras Wafer-Scale Engine for machine learning training.

**application-specific integrated circuit (asic)**: Custom chips designed for specific computational tasks that offer superior performance and energy efficiency compared to general-purpose processors, exemplified by Google's TPUs and Bitcoin mining ASICs

**architectural efficiency**: The dimension of model optimization that focuses on how computations are performed efficiently during training and inference by exploiting sparsity, factorizing large components, and dynamically adjusting computation based on input complexity.

**artificial general intelligence**: A hypothetical form of AI that matches or exceeds human cognitive abilities across all domains, representing the ultimate goal of AI research beyond current narrow AI systems.

**artificial intelligence**: The field of computer science focused on creating systems that can perform tasks typically requiring human intelligence, such as perception, reasoning, learning, and decision-making.

**artificial neural network**: A computational model inspired by biological neural networks, consisting of interconnected nodes (neurons) organized in layers that can learn patterns from data through adjustable weights and biases.

**artificial neurons**: Basic computational units in neural networks that mimic biological neurons, taking multiple inputs, applying weights and biases, and producing an output signal through an activation function.

**attack taxonomy**: Systematic classification of cybersecurity threats and adversarial attacks against ML systems, organizing threats by method, target, and impact to guide defense strategies.

**attention mechanism**: A neural network component that computes weighted connections between elements based on their content, allowing dynamic focus on relevant parts of the input rather than fixed architectural connections.

**autoencoder**: A neural network architecture that learns compressed data representations by minimizing reconstruction error, commonly used for anomaly detection and dimensionality reduction.

**automatic differentiation**: A computational technique that automatically calculates exact derivatives of functions implemented as computer programs by systematically applying the chain rule at the elementary operation level, essential for training neural networks through gradient-based optimization.

**automatic mixed precision**: A training technique that automatically manages the use of different numerical precisions (FP16, FP32) to optimize memory usage and computational speed while maintaining model accuracy.

**automation bias**: The tendency for humans to over-rely on automated system outputs even when clear errors are present, potentially compromising human oversight.

**automl**: Automated Machine Learning that uses machine learning itself to automate model design decisions, including architecture search, hyperparameter optimization, and feature selection to create efficient models without manual intervention

**autoregressive**: Models that generate sequences by predicting the next element based on previous elements, such as GPT models that generate text one token at a time.

**autoscaling**: Dynamic adjustment of compute resources based on workload demand, automatically scaling up during peak usage and scaling down during low usage to optimize costs and performance.

**availability attack**: A type of data poisoning attack that aims to degrade the overall performance of a machine learning model by introducing noise or corrupting training data across multiple classes.

## B

**backdoor attack**: A type of data poisoning where hidden triggers are embedded in training data, causing models to behave maliciously when specific patterns are encountered during inference

**backpropagation**: An algorithm that computes gradients of the loss function with respect to network weights by propagating error signals backward through the network layers, enabling systematic weight updates during training.

**bandwidth**: The maximum rate of data transfer across a communication channel or memory interface, typically measured in bytes per second and critical for optimizing data movement in AI accelerators.

**batch inference**: The process of using a trained machine learning model to make predictions or decisions on new, previously unseen data.

**batch ingestion**: A data processing pattern that collects and processes data in groups or batches at scheduled intervals, suitable for scenarios where real-time processing is not critical.

**batch normalization**: A technique that normalizes inputs to each layer to have zero mean and unit variance, which stabilizes training and often allows for higher learning rates and faster convergence.

**batch processing**: The technique of processing multiple data samples simultaneously to amortize computation and memory access costs, improving overall throughput in neural network training and inference

**batch size**: The number of training examples processed simultaneously during one iteration of neural network training, affecting both computational efficiency and gradient estimation quality.

**batch throughput optimization**: Techniques for maximizing the number of samples processed per unit time when handling multiple inputs simultaneously, leveraging parallelism and batching efficiencies.

**batched operations**: Matrix computations that process multiple inputs simultaneously, converting matrix-vector operations into more efficient matrix-matrix operations to improve hardware utilization.

**bayesian neural networks**: Neural networks that incorporate probability distributions over their weights, enabling uncertainty quantification in predictions and more robust decision making.

**benchmark engineering**: The systematic design and development of performance evaluation frameworks, involving test harness creation, metric selection, and result interpretation methodologies.

**benchmark harness**: Systematic infrastructure component that controls test execution, manages input delivery, and collects performance measurements under controlled conditions to ensure reproducible evaluations.

**benchmarking**: Systematic evaluation of compute performance, algorithmic effectiveness, and data quality in machine learning systems to optimize performance across diverse workloads and ensure reproducibility.

**bert**: Bidirectional Encoder Representations from Transformers, a transformer-based language model introduced by Google in 2018 that revolutionized natural language processing through masked language modeling pre-training.

**bfloat16**: A 16-bit floating-point format developed by Google Brain that maintains the same dynamic range as FP32 but with reduced precision, making it particularly suitable for deep learning training.

**bias**: A learnable parameter added to the weighted sum in each neuron that allows the activation function to shift, providing additional flexibility for the network to fit complex patterns.

**bias detection**: Systematic methods for identifying unfair discrimination or disparate treatment across different demographic groups in machine learning system outputs.

**bias mitigation**: Techniques and interventions designed to reduce unfair discrimination in machine learning systems, applied during data collection, model training, or post-processing stages.

**bias terms**: Learnable parameters in neural networks that shift the activation function, allowing neurons to activate even when all inputs are zero, providing additional flexibility for fitting complex patterns.

**bias-only adaptation**: A lightweight training strategy that freezes all model weights and updates only scalar bias terms, drastically reducing memory requirements and computational overhead for on-device learning.

**binarization**: An extreme quantization technique that reduces neural network weights and activations to binary values (typically -1 and +1), achieving maximum compression but often requiring specialized training procedures and hardware support.

**biodiversity monitoring**: The systematic observation and measurement of biological diversity using technology such as camera traps and sensor networks to track species populations, habitat changes, and conservation effectiveness.

**biological neuron**: A cell in the nervous system that receives, processes, and transmits information through electrical and chemical signals, serving as inspiration for artificial neural networks.

**bit flip**: A hardware fault where a single bit in memory or a register unexpectedly changes its value from 0 to 1 or vice versa, potentially corrupting data or computations.

**black box**: A system where you can observe the inputs and outputs but cannot see or understand the internal workings, particularly problematic in AI when systems make important decisions affecting people's lives without providing explanations for their reasoning.

**black-box attack**: An adversarial attack where the attacker has no knowledge of the model's internal architecture, parameters, or training data, and must rely solely on querying the model and observing outputs.

**blas**: Basic Linear Algebra Subprograms, a specification for low-level routines that perform common linear algebra operations such as vector addition, scalar multiplication, dot products, and matrix operations, forming the computational foundation of modern ML frameworks.

**bounding box**: A rectangular annotation that identifies object locations in images by drawing a box around each object of interest, commonly used in computer vision training datasets.

**brain-computer interface**: A direct communication pathway between the brain and an external device, enabling control of computers or prosthetics through neural signals and representing a convergence of ML with neurotechnology.

**brittleness**: The tendency of rule-based AI systems to fail completely when encountering inputs that fall outside their programmed scenarios, no matter how similar those inputs might be to what they were designed to handle.

**built-in self-test (bist)**: Hardware testing mechanisms that allow components to test themselves for faults using dedicated circuitry and predefined test patterns.

## C

**cache timing attack**: A type of side-channel attack that exploits variations in memory cache access patterns to infer sensitive information about program execution or data.

**caching**: A technique for storing frequently accessed data in high-speed storage systems to reduce retrieval latency and improve system performance in ML pipelines.

**calibration**: The process in post-training quantization of analyzing a representative dataset to determine optimal quantization parameters, including scale factors and zero points, that minimize accuracy loss when converting from high to low precision.

**canary deployment**: Gradual rollout strategy where a new model version serves a small percentage of traffic while monitoring performance before full deployment, allowing safe validation in production.

**carbon footprint**: The total amount of greenhouse gas emissions produced directly and indirectly by an individual, organization, event, or product, typically measured in CO2 equivalent.

**carbon-aware scheduling**: A computational approach that schedules AI workloads based on the carbon intensity of the electricity grid, prioritizing execution when renewable energy sources are most available.

**catastrophic forgetting**: The phenomenon where neural networks lose previously learned knowledge when adapting to new tasks, a critical challenge in continual on-device learning scenarios.

**cerebras wafer-scale engine**: A revolutionary single-wafer processor containing 2.6 trillion transistors and 850,000 cores, designed to eliminate inter-device communication bottlenecks in large-scale machine learning training.

**channelwise quantization**: A quantization granularity approach where each channel in a layer uses its own set of quantization parameters, providing more precise representation than layerwise quantization while maintaining hardware efficiency.

**checkpoint and restart mechanisms**: Techniques that periodically save a program's state so it can resume from the last saved state after a failure, improving system resilience.

**ci/cd pipelines**: Continuous Integration and Continuous Delivery automated workflows that streamline model development by integrating testing, validation, and deployment processes.

**cifar10**: Canadian Institute for Advanced Research dataset with 60,000 32×32 color images across 10 classes, serving as a standard benchmark in computer vision despite its small image size by modern standards.

**classification labels**: Simple categorical annotations that assign specific tags or categories to data examples, representing the most basic form of supervised learning annotation.

**client scheduling**: The process of selecting which devices participate in federated learning rounds based on availability, data quality, and resource constraints to ensure representative model updates.

**cloud ml**: Machine learning systems that leverage cloud computing infrastructure to provide scalable computational resources for training and inference, typically offering high-bandwidth connectivity and substantial processing power.

**cloudsuite**: Benchmark suite developed at EPFL that addresses modern datacenter workloads including web search, data analytics, and media streaming, measuring end-to-end performance across network, storage, and compute dimensions.

**co design**: Holistic approach where model architectures, hardware platforms, and data pipelines are designed in tandem to work seamlessly together, mitigating trade-offs through end-to-end optimization.

**cold-start performance**: Time required for a system to transition from idle state to active execution, particularly important in serverless environments where models are loaded on demand.

**combinational logic**: Digital logic circuits where the output depends only on the current input states, not any past states or memory elements.

**compound ai systems**: AI architectures that combine multiple specialized models and components working together, rather than relying on a single monolithic model, enabling modularity, specialization, and improved interpretability

**computational graph**: A directed acyclic graph representation of mathematical operations where nodes represent operations or variables and edges represent data flow, enabling automatic differentiation and optimization of neural network computations.

**compute efficiency**: The optimization of computational resources including hardware and energy utilization to maximize processing speed while minimizing resource consumption during training and deployment.

**compute-optimal training**: Training strategies that optimally balance model size and training compute budget according to scaling laws, achieving maximum performance for a given computational budget.

**computer engineering**: An engineering discipline that emerged in the late 1960s to address the growing complexity of integrating hardware and software systems, combining expertise from electrical engineering and computer science to design and build complex computing systems.

**concept bottleneck models**: Neural network architectures that first predict interpretable intermediate concepts before making final predictions, combining deep learning power with transparency.

**concept drift**: Performance degradation that occurs when the underlying relationship between input features and target outcomes changes over time, requiring model retraining

**conditional computation**: A dynamic optimization technique where different parts of a neural network are selectively activated based on input characteristics, reducing computational load by skipping unnecessary computations for specific inputs.

**connectionism**: An approach to AI modeling that emphasizes learning and intelligence emerging from simple interconnected units, serving as the theoretical foundation for neural networks and contrasting with symbolic AI approaches.

**consensus labeling**: A quality control approach that collects multiple annotations for the same data point to identify controversial cases and improve label reliability through inter-annotator agreement.

**conservation technology**: Technological solutions designed to protect and monitor wildlife and ecosystems, including camera traps, sensor networks, and satellite monitoring systems for tracking animal behavior and detecting threats.

**constitutional ai**: A training method where models learn to improve their own outputs by critiquing responses against a set of principles, enabling iterative self-refinement and reducing harmful content while maintaining helpfulness

**containerization**: Packaging applications and their dependencies into portable, isolated containers using tools like Docker to ensure consistent execution across different environments.

**containerized microservices**: Architectural pattern using lightweight containers to package individual services, enabling scalable, maintainable deployment of ML systems across distributed environments.

**continual learning**: The ability of machine learning systems to learn continuously from a stream of data while retaining previously acquired knowledge, addressing the challenge of catastrophic forgetting in neural networks

**continuous integration**: A software development practice where code changes are automatically integrated, tested, and validated multiple times per day to detect issues early in the development cycle.

**convolution**: A mathematical operation fundamental to convolutional neural networks that applies filters (kernels) to input data to extract features such as edges, textures, or patterns, particularly effective for processing images and spatial data.

**convolution operation**: A mathematical operation that slides a filter (kernel) across input data to detect local features, forming the foundation of convolutional neural networks for spatial pattern recognition.

**convolutional neural network**: A specialized neural network architecture designed for processing grid-like data such as images, using convolutional layers that apply filters to detect local features.

**cooling effectiveness**: The efficiency with which a data center cooling system removes heat from computing equipment, typically measured as the ratio of heat removed to energy consumed for cooling.

**counterfactual explanations**: Explanations that describe how a model's output would change if specific input features were modified, particularly useful for understanding decision boundaries.

**covariate shift**: A type of distribution shift where the input distribution changes while the conditional relationship between inputs and outputs remains stable.

**cp decomposition**: CANDECOMP/PARAFAC decomposition that expresses a tensor as a sum of rank-one components, used to compress neural network layers by reducing the number of parameters while preserving computational functionality.

**crisp-dm**: Cross-Industry Standard Process for Data Mining, a structured methodology developed in 1996 that defines six phases for data projects: business understanding, data understanding, data preparation, modeling, evaluation, and deployment.

**cross-entropy loss**: A loss function commonly used in classification tasks that measures the difference between predicted probability distributions and true class labels, providing strong gradients for effective learning.

**crowdsourcing**: A collaborative data collection approach that leverages distributed individuals via the internet to perform annotation tasks, enabling scalable dataset creation through platforms like Amazon Mechanical Turk.

**cublas**: NVIDIA's CUDA Basic Linear Algebra Subprograms library that provides GPU-accelerated implementations of standard linear algebra operations, enabling high-performance matrix computations on NVIDIA graphics processing units.

**cuda**: NVIDIA's parallel computing platform and programming model that enables general-purpose computing on graphics processing units (GPUs), allowing machine learning frameworks to leverage massive parallelism for accelerated tensor operations.

**cuda (compute unified device architecture)**: NVIDIA's parallel computing platform and programming model that enables developers to use GPUs for general-purpose computing beyond graphics rendering.

**curriculum learning**: Training strategy where models learn from easy examples before progressing to harder ones, mimicking human education and improving convergence speed by 25-50%.

## D

**dartmouth conference**: The legendary 8-week workshop at Dartmouth College in 1956 where AI was officially born, organized by John McCarthy, Marvin Minsky, Nathaniel Rochester, and Claude Shannon, where the term "artificial intelligence" was first coined.

**data augmentation**: Artificially expanding datasets through transformations like rotations, crops, or noise to improve model performance by 5-15% and reduce overfitting when labeled data is scarce

**data cascades**: Systemic failures where data quality issues compound over time, creating downstream negative consequences such as model failures, costly rebuilding, or project termination.

**data center**: A facility that houses computer systems and associated components such as telecommunications and storage systems, typically containing thousands of servers for cloud computing operations.

**data centric ai**: Paradigm shift from model-centric to data-centric development that focuses on systematically improving data quality rather than just model architecture, often yielding greater performance gains.

**data compression**: Techniques for reducing the size and complexity of training data through encoding, quantization, or feature extraction to enable efficient storage and processing on memory-constrained devices.

**data curation**: The process of selecting, organizing, and maintaining high-quality datasets by removing irrelevant information, correcting errors, and ensuring data meets specific standards for machine learning applications.

**data drift**: The phenomenon where the statistical properties of input data change over time, causing machine learning model performance to degrade even when the underlying code remains unchanged

**data efficiency**: Optimizing the amount and quality of data required to train machine learning models effectively, focusing on maximizing information gained while minimizing required data volume.

**data governance**: The framework of policies, procedures, and technologies that ensure data security, privacy, compliance, and ethical use throughout the machine learning pipeline.

**data ingestion**: The process of collecting and importing raw data from various sources into a system where it can be stored, processed, and prepared for machine learning applications

**data lake**: A storage repository that holds structured, semi-structured, and unstructured data in its native format, using schema-on-read approaches for flexible data analysis.

**data lineage**: The documentation and tracking of data flow through various transformations and processes, providing visibility into data origins and modifications for compliance and debugging

**data parallelism**: A distributed training strategy that splits the dataset across multiple devices while each device maintains a complete copy of the model, enabling parallel computation of gradients.

**data pipeline**: The infrastructure and workflows that automate the movement and transformation of data from sources through processing stages to final storage or consumption.

**data poisoning**: An attack method where adversaries inject carefully crafted malicious data points into the training dataset to manipulate model behavior in targeted or systematic ways

**data quality**: The degree to which data meets requirements for accuracy, completeness, consistency, and timeliness, directly impacting machine learning model performance.

**data sanitization**: The process of deliberately and permanently removing or destroying data stored on memory devices to make it unrecoverable, ensuring data security.

**data scaling regimes**: Different phases of model training where data requirements scale according to predictable patterns, informing decisions about dataset size versus computational investment.

**data validation**: The systematic verification that collected data meets quality standards, is properly formatted, and contains accurate information suitable for machine learning model training and evaluation

**data versioning**: The practice of tracking and managing different versions of datasets over time, similar to code versioning, to ensure reproducibility and enable rollback to previous data states when needed

**data warehouse**: A centralized repository optimized for analytical queries (OLAP) that stores integrated, structured data from multiple sources in a standardized schema.

**data-centric approach**: A machine learning paradigm that prioritizes improving data quality, diversity, and curation rather than solely focusing on model architecture improvements to achieve better performance.

**dataflow architecture**: Specialized computing architecture where instruction execution is determined by data availability rather than a program counter, enabling highly parallel processing of neural network operations.

**dataflow challenges**: Technical difficulties in managing data movement and dependencies in hardware accelerators, including memory bandwidth limitations and synchronization requirements.

**dead letter queue**: A separate storage mechanism for data that fails processing, allowing for later analysis and potential reprocessing of problematic data without blocking the main pipeline.

**deep learning**: A subfield of machine learning that uses artificial neural networks with multiple layers to automatically learn hierarchical representations from data without explicit feature engineering.

**defensive distillation**: A technique that trains a student model to mimic a teacher model's behavior using soft labels, reducing sensitivity to adversarial perturbations.

**demographic parity**: A fairness criterion requiring that the probability of receiving a positive prediction is independent of group membership across protected attributes.

**dennard scaling**: The historical observation that as transistors become smaller, their power density remains approximately constant, allowing for more transistors without proportional increases in power consumption.

**dense layer**: A fully-connected neural network layer where each neuron receives input from all neurons in the previous layer, enabling comprehensive information integration across features.

**dense matrix-matrix multiplication**: The fundamental computational operation in neural networks that dominates training time, accounting for 60-90% of computation in typical models.

**deployment constraints**: Operational limitations such as hardware resources, network connectivity, regulatory requirements, and integration requirements that influence how machine learning models are implemented in production environments.

**depthwise separable convolutions**: A computational technique that decomposes standard convolutions into depthwise and pointwise operations, reducing parameters and computation by 8-9x for mobile-optimized architectures.

**devops**: Software development practice that combines development and operations teams to shorten development cycles and deliver high-quality software through automation and collaboration.

**dhrystone**: Integer-based benchmark introduced in 1984 that measures integer and string operations in DMIPS (Dhrystone MIPS), designed to complement floating-point benchmarks with typical programming constructs.

**diabetic retinopathy**: A diabetes complication that damages blood vessels in the retina, serving as a leading cause of preventable blindness and a key application area for medical AI screening systems.

**differential privacy**: A mathematical framework that provides formal privacy guarantees by adding calibrated noise to computations, ensuring that the inclusion or exclusion of any individual's data has a provably limited effect on the output

**digital divide**: The gap between those who have access to modern information and communication technology and those who do not, particularly affecting underserved communities' ability to benefit from digital solutions.

**digital twin**: A virtual representation of a physical system that uses real-time data and machine learning to mirror, predict, and optimize the behavior of its physical counterpart.

**disaster response systems**: Automated systems that use machine learning to detect, predict, and respond to natural disasters through satellite imagery analysis, sensor networks, and resource allocation optimization.

**distributed computing**: An approach that processes data across multiple machines or processors simultaneously, enabling scalable handling of large datasets through frameworks like Apache Spark.

**distributed intelligence**: The placement of computational capabilities across multiple devices and locations rather than relying on a single centralized system, enabling local processing and decision-making.

**distributed knowledge pattern**: A design pattern that addresses collective learning and inference across decentralized nodes, emphasizing peer-to-peer knowledge sharing and collaborative model improvement while maintaining operational independence.

**distributed training**: A method of training machine learning models across multiple machines or devices to handle larger datasets and models that exceed single-device computational or memory capacity.

**distribution shift**: The phenomenon where data encountered during model deployment differs from the training distribution, potentially degrading model performance

**distribution shift types**: Formal categorization of changes in data distributions including covariate shift, label shift, concept drift, and domain shift, each requiring specific adaptation techniques.

**domain adaptation**: Machine learning techniques that enable models trained on one domain to perform well on a different but related domain, addressing distribution mismatch challenges.

**domain-specific ai applications**: Machine learning solutions tailored to specific sectors like healthcare, agriculture, education, or disaster response, designed to address unique challenges and constraints.

**domain-specific architecture**: Hardware designs tailored to optimize specific computational workloads, trading flexibility for improved performance and energy efficiency compared to general-purpose processors.

**double modular redundancy (dmr)**: A fault-tolerance technique where computations are duplicated across two independent systems to identify and correct errors through comparison.

**dropout**: A regularization technique that randomly sets a fraction of input units to zero during training to prevent overfitting and improve generalization.

**dual-use dilemma**: The challenge of mitigating misuse of technology that has both positive and negative potential applications, particularly relevant in AI security.

**dying relu problem**: A phenomenon where ReLU neurons become permanently inactive and output zero for all inputs, preventing them from contributing to learning when weighted inputs consistently produce negative values.

**dynamic graph**: A computational graph that is built and modified during program execution, allowing for flexible model architectures and easier debugging but potentially limiting optimization opportunities compared to static graphs.

**dynamic pruning**: A model optimization technique that removes unnecessary parameters from neural networks while maintaining predictive performance, reducing model size and computational cost by eliminating redundant weights, neurons, or layers.

**dynamic quantization**: The process of reducing numerical precision in neural networks by mapping high-precision weights and activations to lower-bit representations, significantly reducing memory usage and computational requirements

**dynamic random access memory (dram)**: A type of volatile memory that stores data in capacitors and requires periodic refresh cycles, commonly used as main memory in computer systems.

**dynamic voltage and frequency scaling (dvfs)**: Power management technique that adjusts processor voltage and clock frequency based on workload demands to optimize energy consumption while maintaining performance.

## E

**eager execution**: An execution mode where operations are evaluated immediately as they are called in the code, providing intuitive debugging and development experience but potentially sacrificing some optimization opportunities available in graph-based execution.

**early exit architectures**: Neural network designs that include multiple prediction heads at different depths, allowing samples to exit early when confident predictions can be made, reducing average computational cost per inference.

**edge ai**: The deployment of artificial intelligence algorithms directly on edge devices like smartphones, IoT sensors, and embedded systems, enabling real-time processing without cloud connectivity.

**edge computing**: A distributed computing paradigm that brings computation and data storage closer to the sources of data, reducing latency and bandwidth usage.

**edge deployment**: A deployment strategy where machine learning models run locally on devices at the network edge rather than in centralized cloud servers, reducing latency and enabling operation without constant internet connectivity.

**edge ml**: Machine learning systems that perform inference and sometimes training at the edge of networks, typically on resource-constrained devices like smartphones or embedded systems with limited computational power.

**edge training**: The process of training or fine-tuning machine learning models directly on edge devices, enabling personalization and adaptation without requiring data transmission to cloud servers.

**efficientnet**: A family of neural network architectures discovered through Neural Architecture Search that achieves better accuracy-efficiency trade-offs by using compound scaling to balance network depth, width, and input resolution

**electromigration**: The movement of metal atoms in a conductor under the influence of an electric field, potentially causing permanent hardware faults over time.

**eliza**: One of the first chatbots created by MIT's Joseph Weizenbaum in 1966 that could simulate human conversation through pattern matching and substitution, notable because people began forming emotional attachments to this simple program.

**elt (extract, load, transform)**: A data processing paradigm that first loads raw data into the target system before applying transformations, providing flexibility for evolving analytical needs.

**embedded systems**: Computer systems with dedicated functions within larger mechanical or electrical systems, typically designed for specific tasks with real-time computing constraints.

**embodied carbon**: The total greenhouse gas emissions generated during the manufacturing, transportation, and installation of a product before it begins operation.

**emergent behaviors**: Unexpected system-wide patterns or characteristics that arise from the interaction of individual components, often becoming apparent only when systems operate at scale or in real-world conditions.

**emergent capabilities**: Abilities that appear suddenly in neural networks at specific parameter thresholds, such as reasoning and arithmetic skills that emerge discontinuously rather than gradually improving with scale.

**encoder-decoder**: An architectural pattern where an encoder processes input into a compressed representation and a decoder generates output from this representation, commonly used in sequence-to-sequence tasks.

**end-to-end benchmarks**: Comprehensive evaluation methodology that assesses entire AI system pipelines including data processing, model execution, post-processing, and infrastructure components.

**energy efficiency**: The measure of computational work performed per unit of energy consumed, typically expressed as operations per joule and crucial for battery-powered and data center deployments

**energy star**: EPA certification program that establishes energy efficiency standards for computing equipment, requiring systems to meet strict efficiency requirements during operation and sleep modes.

**ensemble methods**: Techniques combining multiple models to improve performance, like Random Forest and Gradient Boosting, which dominated machine learning competitions before deep learning

**environmental impact measurement**: Systematic tracking and quantification of the ecological effects of AI systems, including energy consumption, carbon emissions, and resource depletion across the complete system lifecycle.

**environmental monitoring**: The systematic collection and analysis of environmental data using sensor networks and machine learning to track ecosystem health, pollution levels, and climate change impacts.

**epoch**: One complete pass through the entire training dataset during neural network training, consisting of multiple batch iterations depending on dataset size and batch size.

**equality of opportunity**: A fairness criterion focused on ensuring equal true positive rates across groups, guaranteeing that qualified individuals are treated equally regardless of group membership.

**equalized odds**: A fairness definition requiring that true positive and false positive rates are equal across different demographic groups.

**error-correcting codes**: Methods used in data storage and transmission to detect and correct errors, improving system reliability and data integrity.

**esp32**: A low-cost microcontroller unit widely used in IoT applications, featuring a 240 MHz processor and 520 KB of RAM, commonly deployed in resource-constrained social impact applications.

**etl (extract, transform, load)**: A traditional data processing paradigm that transforms data before loading it into a data warehouse, resulting in ready-to-query formatted data.

**exact model theft**: An attack that aims to extract the precise internal structure, parameters, and architecture of a machine learning model, allowing complete reproduction of the original model.

**experience replay**: A memory-based technique that stores past training examples in a buffer to prevent catastrophic forgetting and stabilize learning in streaming or continual adaptation scenarios.

**experiment tracking**: The systematic recording and management of machine learning experiments, including hyperparameters, model versions, training data, and performance metrics, to enable comparison and reproducibility

**expert collapse**: A training pathology in mixture of experts models where only a few experts receive significant training signal, causing other experts to become underutilized and reducing the model's effective capacity.

**expert systems**: AI systems from the mid-1970s that captured human expert knowledge in specific domains, exemplified by MYCIN for diagnosing blood infections, representing a shift from general AI to domain-specific applications.

**explainability**: The ability of stakeholders to understand how a machine learning model produces its outputs through post-hoc explanation techniques.

**explainable ai**: AI systems designed to provide clear, interpretable explanations for their decisions and predictions, addressing the "black box" problem of complex machine learning models.

**external memory**: Mechanisms that allow neural networks to access and manipulate external storage systems, extending their working memory beyond parameter storage to enable more complex reasoning and information retrieval.

## F

**f1 score**: A measure of model accuracy that combines precision and recall into a single metric, calculated as their harmonic mean.

**fairness constraints**: Technical and policy restrictions designed to ensure equitable treatment across demographic groups in machine learning systems.

**farmbeats**: A Microsoft Research project that applies machine learning and IoT technologies to agriculture, using edge computing to collect real-time data on soil conditions and crop health while demonstrating distributed AI systems in challenging real-world environments.

**fast gradient sign method (fgsm)**: A gradient-based adversarial attack that generates adversarial examples by adding small perturbations in the direction of the gradient.

**fault injection attack**: A physical attack that deliberately disrupts hardware operations through techniques like voltage manipulation or electromagnetic interference to induce computational errors and compromise system integrity.

**fault tolerance**: The ability of a system to continue operating correctly even when some of its components fail or encounter errors.

**feature engineering**: The process of manually designing and extracting relevant features from raw data to improve machine learning model performance, largely automated in deep learning systems.

**feature map**: The output of a convolutional layer representing the response of learned filters to different spatial locations in the input, capturing detected features at various positions.

**feature store**: A specialized data storage system that provides standardized, reusable features for machine learning, enabling feature sharing across multiple models and teams

**federated averaging**: The standard algorithm for federated learning where client model updates are aggregated using weighted averaging based on local dataset sizes to produce a global model.

**federated learning**: A machine learning approach that trains algorithms across decentralized edge devices or servers holding local data samples, without exchanging the raw data.

**feedback loops**: Cyclical processes where outputs from later stages of the machine learning lifecycle inform and influence decisions in earlier stages, enabling continuous system improvement and adaptation.

**feedforward network**: A neural network architecture where information flows in one direction from input to output layers without cycles, forming the foundation for many deep learning models.

**few-shot learning**: A machine learning paradigm that enables models to adapt to new tasks using only a small number of labeled examples, critical for data-sparse on-device scenarios.

**field-programmable gate array**: Reconfigurable hardware that can be programmed for specific tasks, offering flexibility between general-purpose processors and application-specific integrated circuits, useful for custom ML accelerations.

**field-programmable gate array (fpga)**: A reconfigurable integrated circuit that can be programmed after manufacturing to implement custom digital circuits and specialized computations.

**floating-point unit (fpu)**: A specialized processor component designed to perform arithmetic operations on floating-point numbers with high precision and efficiency.

**flops**: Floating Point Operations Per Second, a measure of computational throughput that quantifies the number of mathematical operations involving decimal numbers a system can perform.

**forward pass**: The computation phase where input data flows through a neural network's layers to produce outputs, involving matrix multiplications and activation function applications.

**forward propagation**: The process of computing neural network predictions by passing input data through successive layers, applying weights, biases, and activation functions at each stage.

**foundation model**: Large-scale machine learning models trained on broad data that can be adapted to a wide range of downstream tasks, serving as a base for specialized applications.

**foundation models**: Large-scale, general-purpose AI models trained on broad data that can be adapted for many tasks, including models like GPT-3, BERT, and DALL-E with billions of parameters

**fp16**: 16-bit floating-point numerical representation that reduces memory usage and accelerates computation while maintaining acceptable precision for many machine learning applications.

**fp16 computation**: The use of 16-bit floating-point arithmetic for neural network operations to reduce memory usage and increase computational speed on modern hardware accelerators.

**fp32**: 32-bit floating-point numerical representation that provides standard precision for mathematical computations but requires more memory and computational resources than lower-precision formats.

**fp32 to int8**: A common quantization transformation that converts 32-bit floating point weights and activations to 8-bit integers, achieving roughly 4x memory reduction while maintaining acceptable accuracy for many models.

**framework decomposition**: The systematic breakdown of neural network frameworks into hardware-mappable components, enabling efficient distribution of operations across processing elements.

## G

**gdpr**: The General Data Protection Regulation, a European Union law that imposes strict requirements on personal data processing and significantly influences privacy-preserving machine learning design

**gemm**: General Matrix Multiply operations that follow the pattern C = αAB + βC, representing the fundamental computational kernel underlying most neural network operations including fully connected layers and convolutional layers.

**gemv**: General Matrix-Vector multiplication operations that compute the product of a matrix and a vector, commonly used in neural network computations and requiring careful optimization for memory access patterns.

**generalization**: The ability of a machine learning model to perform well on unseen data that differs from the training set, often improved through diverse and high-quality training data.

**generative adversarial networks**: A class of machine learning systems where two neural networks compete against each other, with one generating fake data and the other trying to detect it, leading to highly realistic synthetic data generation.

**generative ai**: A category of artificial intelligence systems capable of creating new content such as text, images, audio, or video based on learned patterns from training data.

**glitches**: Momentary deviations in voltage, current, or signal that can cause incorrect operation in digital systems and circuits.

**governance frameworks**: Structured approaches for managing responsible AI development including policies, procedures, oversight mechanisms, and accountability structures.

**gpt3**: OpenAI's 175-billion parameter language model released in 2020, costing an estimated $4.6 million to train and consuming approximately 1,287 MWh of electricity.

**gpt4**: OpenAI's most advanced language model as of 2023, reportedly using a mixture-of-experts architecture with approximately 1.8 trillion parameters and training costs exceeding $100 million.

**gpu**: Graphics Processing Unit, a specialized electronic circuit designed to rapidly manipulate and alter memory to accelerate the creation of images and parallel processing tasks.

**graceful degradation**: A system design principle where services continue functioning with reduced capabilities when faced with partial failures or data unavailability.

**gradient accumulation**: A technique that simulates larger batch sizes by accumulating gradients from multiple smaller batches before updating model parameters, enabling training with limited memory.

**gradient clipping**: A regularization technique that prevents gradient explosion by limiting the magnitude of gradients during backpropagation, typically by scaling gradients when their norm exceeds a threshold.

**gradient compression**: A technique used in distributed training to reduce the communication overhead by compressing gradient information exchanged between computing nodes.

**gradient descent**: An optimization algorithm that iteratively adjusts neural network parameters in the direction that minimizes the loss function, using gradients to determine update directions and magnitudes.

**gradient synchronization**: The process in distributed training where locally computed gradients are aggregated across devices to ensure all devices update their parameters consistently.

**gradient-based pruning**: A pruning method that uses gradient information during training to identify neurons or filters with smaller gradient magnitudes, which contribute less to reducing the loss function and can be safely removed.

**graphics processing unit**: A specialized processor originally designed for rendering graphics that provides parallel processing capabilities essential for efficient neural network computation and training.

**graphics processing unit (gpu)**: A specialized processor originally designed for graphics rendering that provides massive parallel computing capabilities well-suited for neural network computations.

**green ai metrics**: Specialized performance indicators that measure the environmental impact of AI systems, including carbon footprint, energy efficiency, and resource utilization throughout the ML lifecycle.

**green computing**: The practice of designing, manufacturing, using, and disposing of computers and computer systems in an environmentally responsible manner.

**green500**: Ranking system that evaluates the world's most powerful supercomputers based on energy efficiency measured in FLOPS per watt rather than raw computational performance.

**grey-box attack**: An adversarial attack where the attacker has partial knowledge about the model, such as knowing the architecture but not the specific parameters or training data.

**groupwise quantization**: A quantization approach where parameters are divided into groups, with each group sharing quantization parameters, offering a balance between compression and accuracy by providing more granular control than layerwise methods.

**gru**: Gated Recurrent Unit, a simplified variant of LSTM that uses fewer gates while maintaining the ability to capture long-term dependencies in sequential data.

## H

**hardware abstraction**: The layer in ML frameworks that provides a unified interface to diverse computing hardware (CPUs, GPUs, TPUs, accelerators) while handling device-specific optimizations and memory management behind the scenes.

**hardware acceleration**: The use of specialized computing hardware to perform certain operations faster and more efficiently than software running on general-purpose processors.

**hardware accelerator**: Specialized computing hardware designed to efficiently execute specific types of computations, such as GPUs for parallel processing or TPUs for machine learning workloads.

**hardware constraint optimization**: Techniques for adapting ML algorithms and models to work within the memory, compute, and power limitations of mobile and embedded devices.

**hardware redundancy**: The duplication of critical hardware components to provide backup functionality and improve system reliability through voting mechanisms.

**hardware trojan**: A malicious modification embedded in hardware components during manufacturing that can remain dormant under normal conditions but trigger harmful behavior when specific conditions are met.

**hardware-aware design**: The practice of designing neural network architectures specifically optimized for target hardware platforms, considering factors like memory hierarchy, compute units, and data movement patterns to maximize efficiency.

**hardware-software co-design**: Collaborative design methodology where hardware accelerators and software algorithms are jointly optimized to achieve maximum efficiency and performance.

**hdfs (hadoop distributed file system)**: A distributed file system designed to store large datasets across clusters of commodity hardware, providing scalability and fault tolerance for big data applications.

**heartbeat mechanisms**: Periodic signals sent between system components to monitor health and detect failures, enabling timely fault detection and recovery.

**hidden layer**: An intermediate layer in a neural network between input and output layers that learns abstract representations by transforming data through learned weights and activation functions.

**hidden state**: The internal memory of recurrent neural networks that carries information from previous time steps, enabling the network to maintain context across sequential inputs.

**hierarchical processing**: A multi-tier system architecture where data and intelligence flow between different levels of the computing stack, from sensors to edge devices to cloud systems.

**hierarchical processing pattern**: A design pattern that organizes systems into tiers (edge, regional, cloud) that share responsibilities based on available resources and capabilities, optimizing resource usage across the computing spectrum.

**high bandwidth memory (hbm)**: An advanced memory technology that provides much higher bandwidth than traditional DRAM by using 3D stacking and wide interfaces, critical for data-intensive AI workloads.

**homomorphic encryption**: A cryptographic technique that allows computations to be performed directly on encrypted data without decrypting it first, enabling privacy-preserving machine learning inference.

**horizontal scaling**: Increasing system capacity by adding more machines or instances rather than upgrading existing hardware, providing better fault tolerance and load distribution.

**hot spares**: Backup components kept ready to instantaneously replace failing components without disrupting system operation, providing redundancy.

**huber loss**: A robust loss function used in regression that is less sensitive to outliers compared to squared error loss, improving training stability.

**human oversight**: The principle that human judgment should supervise, correct, or halt automated decisions, maintaining meaningful human control over AI systems.

**human-ai collaboration**: The synergistic partnership between humans and AI systems where each contributes their unique strengths to solve complex problems more effectively than either could alone.

**hybrid machine learning**: The integration of multiple ML paradigms such as cloud, edge, mobile, and tiny ML to form unified distributed systems that leverage complementary strengths.

**hybrid parallelism**: A distributed training approach that combines data parallelism and model parallelism to leverage the benefits of both strategies for training very large models.

**hyperparameter**: A configuration setting that controls the learning process but is not learned from data, such as learning rate, batch size, or network architecture choices.

**hyperparameter optimization**: The process of finding the optimal configuration of hyperparameters (learning rate, batch size, network architecture parameters) that control the machine learning training process.

**hyperparameters**: Configuration settings that control the learning process of machine learning algorithms but are not learned from data, such as learning rate, batch size, and network architecture parameters.

**hyperscale data center**: Large-scale data center facilities containing thousands of servers and covering extensive floor space, designed to efficiently support massive computing workloads.

## I

**imagenet**: A massive visual database containing over 14 million labeled images across 20,000+ categories, created by Stanford's Fei-Fei Li starting in 2009, whose annual challenge became instrumental in driving breakthrough advances in computer vision

**impact assessment frameworks**: Structured methodologies for evaluating the potential social, economic, and environmental effects of AI deployments in humanitarian and development contexts.

**imperative programming**: A programming paradigm where operations are executed immediately as they are encountered in the code, allowing for natural control flow and easier debugging but potentially limiting optimization opportunities.

**inference**: The phase of machine learning where a trained model makes predictions on new input data, typically requiring lower precision and computational resources than training

**infrastructure as code**: Practice of managing and provisioning computing infrastructure through machine-readable configuration files rather than manual processes, enabling version control and automation.

**instruction set architecture (isa)**: The interface between software and hardware that defines the set of instructions a processor can execute, including data types and addressing modes.

**int8**: 8-bit integer numerical representation used in quantized neural networks to reduce memory usage and accelerate inference while attempting to maintain model accuracy.

**int8 quantization**: A numerical precision reduction technique that represents model weights and activations using 8-bit integers instead of 32-bit floating point numbers, reducing memory usage and enabling faster inference on specialized hardware

**intermittent faults**: Hardware faults that occur sporadically and unpredictably, appearing and disappearing without consistent patterns, making diagnosis challenging.

**internet of things**: A network of physical objects embedded with sensors, software, and other technologies that connect and exchange data with other devices and systems over the internet.

**interpretability**: The degree to which humans can understand the reasoning behind a machine learning model's predictions, often referring to inherently transparent models.

**iot sensors**: Internet of Things devices that collect and transmit environmental or behavioral data, often operating on limited power budgets and using low-bandwidth communication protocols.

**iterative pruning**: A gradual pruning strategy that removes parameters in multiple stages with fine-tuning between each stage, allowing the model to adapt to reduced capacity and typically achieving better accuracy than one-shot pruning.

## J

**jax**: A numerical computing library developed by Google Research that combines NumPy's API with functional programming transformations including automatic differentiation, just-in-time compilation, and automatic vectorization for high-performance machine learning research.

**jit compilation**: Just-In-Time compilation that analyzes and optimizes code at runtime, enabling frameworks to balance the flexibility of eager execution with the performance benefits of graph optimization by compiling frequently used functions.

## K

**k-anonymity**: A privacy technique that ensures each record in a dataset is indistinguishable from at least k-1 other records by generalizing quasi-identifiers.

**kernel**: A small matrix of learnable weights used in convolutional layers to detect specific features through the convolution operation, also called a filter.

**kernel fusion**: An optimization technique that combines multiple computational operations into a single kernel to reduce memory transfers and improve performance on parallel processors.

**key performance indicators**: Specific, measurable metrics used to evaluate the success and effectiveness of machine learning systems, such as accuracy, precision, recall, latency, and throughput.

**keyword spotting (kws)**: A technology that detects specific wake words or phrases in audio streams, typically used in voice-activated devices with constraints on power consumption and latency.

**knowledge distillation**: A model compression technique where a smaller "student" network learns to mimic the behavior of a larger "teacher" network by training on the teacher's soft output probabilities rather than just hard labels

## L

**l0-norm constraint**: A regularization technique that counts the number of non-zero parameters in a model, used in structured pruning to directly control model sparsity by penalizing the number of active weights.

**label shift**: A type of distribution shift where the distribution of target labels changes while the conditional relationship between features and labels remains constant.

**lapack**: Linear Algebra Package that extends BLAS with higher-level linear algebra operations including matrix decompositions, eigenvalue problems, and linear system solutions, providing essential mathematical foundations for machine learning computations.

**large language models**: Neural networks with billions or trillions of parameters trained on vast text corpora, capable of understanding and generating human-like text across diverse domains and tasks.

**latency**: The time delay between a request for data and the delivery of that data, critical in real-time applications where immediate responses are required.

**latency constraints**: Real-time requirements that limit the maximum acceptable delay for model inference, driving optimization decisions in deployment scenarios where response time is critical.

**layer normalization**: A normalization technique that normalizes inputs across the features dimension for each sample, commonly used in transformer architectures to stabilize training.

**layerwise quantization**: A quantization granularity where all parameters within a single layer share the same quantization parameters, providing computational efficiency but potentially limiting representational precision compared to finer-grained approaches.

**learning rate**: A hyperparameter that determines the step size for weight updates during gradient descent optimization, critically affecting training stability and convergence speed.

**learning rate scheduling**: The systematic adjustment of learning rates during training, using strategies like step decay, exponential decay, or cosine annealing to improve convergence and final model performance.

**lifecycle assessment**: A systematic approach to evaluating the environmental impacts of a product or system throughout its entire life cycle, from raw material extraction to disposal.

**lifecycle coherence**: The principle that all stages of ML development should align with overall system objectives, maintaining consistency in data handling, model architecture, and evaluation criteria.

**linpack**: Benchmark developed at Argonne National Laboratory that measures system performance by solving dense systems of linear equations, famous for its use in Top500 supercomputer rankings.

**load balancing**: Techniques in mixture of experts models to ensure that computational load and training signal are distributed evenly across experts, preventing expert collapse and maintaining model efficiency

**lookup table**: A data structure that replaces runtime computation with simpler array indexing operations, commonly used for performance optimization.

**lora technology**: Long Range wireless communication protocol that enables IoT devices to communicate over 15+ kilometers with minimal power consumption, ideal for agricultural and environmental monitoring applications.

**loss function**: A mathematical function that quantifies the difference between neural network predictions and true labels, providing the optimization objective for training algorithms.

**loss scaling**: A technique used in mixed-precision training that multiplies the loss by a large factor before backpropagation to prevent gradient underflow in reduced precision formats.

**lottery ticket hypothesis**: The theory that large neural networks contain sparse subnetworks that, when trained in isolation from proper initialization, can achieve comparable accuracy to the full network while being significantly smaller.

**low-rank adaptation**: A parameter-efficient fine-tuning method that approximates weight updates using low-rank matrices, reducing trainable parameters while maintaining adaptation capability.

**low-rank factorization**: A matrix decomposition technique that approximates large weight matrices as products of smaller matrices, reducing the number of parameters and computational operations required for neural network layers.

**lstm**: Long Short-Term Memory, a type of recurrent neural network architecture designed to handle long-term dependencies through gating mechanisms that control information flow.

## M

**machine consciousness**: The hypothetical emergence of conscious awareness in artificial systems, representing a frontier research area exploring whether machines can develop subjective experiences.

**machine learning**: A subset of artificial intelligence that enables systems to automatically improve performance on tasks through experience and data rather than explicit programming.

**machine learning accelerator (ml accelerator)**: Specialized computing hardware designed to efficiently execute machine learning workloads through optimized matrix operations, memory hierarchies, and parallel processing units.

**machine learning framework**: A software platform that provides tools and abstractions for designing, training, and deploying machine learning models, bridging user applications with infrastructure through computational graphs, hardware optimization, and workflow orchestration.

**machine learning frameworks**: Software libraries and platforms that provide tools, APIs, and abstractions for developing, training, and deploying machine learning models, such as TensorFlow and PyTorch.

**machine learning lifecycle**: A structured, iterative process that encompasses all stages involved in developing, deploying, and maintaining machine learning systems, from problem definition through ongoing monitoring and improvement

**machine learning operations**: The practice and set of tools focused on operationalizing machine learning models through automation, monitoring, and management of the entire ML pipeline from development to production.

**machine learning operations (mlops)**: The practice of deploying and maintaining machine learning models in production reliably and efficiently through automated pipelines.

**machine learning security**: The protection of data, models, and infrastructure from unauthorized access, manipulation, or disruption throughout the entire machine learning lifecycle.

**machine learning systems engineering**: The engineering discipline focused on building reliable, efficient, and scalable AI systems across computational platforms, spanning the entire AI lifecycle from data acquisition through deployment and operations with emphasis on resource-awareness and system-level optimization.

**machine unlearning**: Techniques for removing the influence of specific data points from trained models without complete retraining, supporting data deletion rights.

**macro benchmarks**: Evaluation methodology that assesses complete machine learning models to understand how architectural choices and component interactions affect overall system behavior and performance.

**magnitude-based pruning**: The most common pruning method that removes parameters with the smallest absolute values, based on the assumption that weights with smaller magnitudes contribute less to the model's output

**mapping optimization**: The process of assigning neural network operations to hardware resources in a way that minimizes communication overhead and maximizes utilization of available compute units.

**masking**: An anonymization technique that alters or obfuscates sensitive values so they cannot be directly traced back to the original data subject.

**megawatt-hour**: A unit of energy equal to one megawatt of power used for one hour, commonly used to measure electricity consumption in large facilities like data centers.

**membership inference attack**: An attack that attempts to determine whether a specific data point was included in a model's training dataset by analyzing the model's behavior and outputs.

**membership inference attacks**: Privacy attacks that attempt to determine whether a specific data point was included in a model's training set by analyzing model behavior.

**memory bandwidth**: Rate at which data can be read from or written to memory, measured in bytes per second, which often becomes a bottleneck in memory-intensive machine learning workloads.

**memory hierarchy**: The organization of memory systems with different access speeds and capacities, from fast on-chip caches to slower off-chip main memory.

**meta-learning**: The process of learning how to learn, where models are trained to quickly adapt to new tasks with minimal data, particularly useful for personalization in on-device systems

**metadata**: Descriptive information about datasets that includes details about data collection, quality metrics, validation status, and other contextual information essential for data management.

**micro benchmarks**: Specialized evaluation tools that assess individual components or specific operations within machine learning systems, such as tensor operations or neural network layers.

**microcontroller**: A small computer on a single integrated circuit containing a processor core, memory, and programmable input/output peripherals, commonly used in embedded systems.

**mini-batch gradient descent**: A training approach that computes gradients and updates weights using a small subset of training examples simultaneously, balancing computational efficiency with gradient estimation quality.

**mini-batch processing**: An optimization approach that computes gradients over small batches of examples, balancing the computational efficiency of batch processing with the memory constraints of stochastic methods.

**minimax**: A decision-making strategy used in game theory that attempts to minimize the maximum possible loss in adversarial scenarios.

**mixed precision training**: A technique that uses different numerical precisions for different parts of neural network training, typically combining 16-bit and 32-bit floating-point arithmetic to reduce memory usage and increase training speed.

**mixed-precision computing**: A technique that uses different numerical precisions at various stages of computation, such as FP16 for matrix multiplications and FP32 for accumulations.

**mixed-precision training**: A training methodology that combines different numerical precisions (typically FP16 and FP32) to optimize memory usage and computational speed while maintaining training stability.

**mixture of experts**: An architectural approach that uses multiple specialized sub-models (experts) with a gating mechanism to route inputs to the most relevant experts, enabling efficient scaling while maintaining sparsity.

**ml lifecycle**: The iterative process that guides the development, evaluation, and continual improvement of machine learning systems, involving stages from data collection through model monitoring with feedback loops for continuous adaptation

**ml systems**: Integrated computing systems comprising three core components: data that guides algorithmic behavior, learning algorithms that extract patterns from data, and computing infrastructure that enables both training and inference processes.

**ml systems spectrum**: The range of machine learning system deployments from cloud-based systems with abundant resources to tiny embedded devices with severe constraints, each requiring different optimization strategies and trade-offs.

**mlcommons**: Organization that develops and maintains industry-standard benchmarks for machine learning systems, including the MLPerf suite for training and inference evaluation.

**mlops**: Engineering discipline that manages the end-to-end lifecycle of machine learning systems, combining ML development with operational practices for reliable production deployment

**mlperf**: Industry-standard benchmark suite that provides standardized tests for training and inference across various deep learning workloads, enabling fair comparisons of machine learning systems.

**mlperf inference**: Benchmark framework that evaluates machine learning inference performance across different deployment environments, from cloud data centers to mobile devices and embedded systems.

**mlperf mobile**: Specialized benchmark that extends MLPerf evaluation to smartphones and mobile devices, measuring latency and responsiveness under strict power and memory constraints.

**mlperf tiny**: Benchmark designed for embedded and ultra-low-power AI systems such as IoT devices, wearables, and microcontrollers operating with minimal processing capabilities.

**mlperf training**: Standardized benchmark that evaluates machine learning training performance by measuring time-to-accuracy, throughput, and resource utilization across different hardware platforms.

**mnist**: Modified National Institute of Standards and Technology database of handwritten digits containing 70,000 28×28 pixel images, serving as the "Hello World" of computer vision.

**mobile machine learning**: The execution of machine learning models directly on portable, battery-powered devices like smartphones and tablets, enabling personalized and responsive applications.

**mobile ml**: Machine learning systems optimized for mobile devices like smartphones and tablets, balancing computational efficiency with inference accuracy for on-device processing.

**mobile-optimized architectures**: Neural network designs specifically created for mobile deployment, emphasizing parameter efficiency, computational speed, and energy conservation.

**mobilenet**: Efficient neural network architecture using depthwise separable convolutions, achieving approximately 50× fewer parameters than traditional models while enabling smartphone deployment

**mode collapse**: A failure mode in generative models where the model produces only a limited variety of outputs, ignoring the diversity present in the training data and failing to capture the full distribution.

**model cards**: Documentation framework that provides structured information about machine learning models, including intended use, performance characteristics, and limitations.

**model compression**: Techniques used to reduce the size and computational requirements of machine learning models while preserving accuracy, enabling deployment on resource-constrained devices.

**model deployment**: The process of integrating trained machine learning models into production systems where they can make predictions on new data and provide value to end users

**model drift**: The degradation of machine learning model performance over time due to changes in data patterns, user behavior, or environmental conditions that differ from the original training conditions

**model evaluation**: The systematic assessment of machine learning model performance using various metrics and validation techniques to determine whether the model meets requirements and is ready for deployment.

**model extraction**: The process of stealing or recreating a machine learning model by observing its input-output behavior, often through systematic querying of model APIs.

**model inversion attack**: An attack that attempts to reconstruct training data or infer sensitive information about the dataset by analyzing a model's outputs and confidence scores.

**model optimization**: The systematic refinement of machine learning models to enhance their efficiency while maintaining effectiveness, balancing trade-offs between accuracy, computational cost, memory usage, latency, and energy efficiency

**model parallelism**: A distributed training strategy that splits a neural network model across multiple devices, with each device responsible for computing a portion of the network.

**model pruning**: The process of removing unnecessary weights, neurons, or connections from a trained neural network to reduce its size and computational requirements.

**model quantization**: The process of reducing the precision of numerical representations in machine learning models, typically from 32-bit to 8-bit integers, to decrease model size and increase inference speed.

**model registry**: Centralized repository for storing, versioning, and managing trained machine learning models with associated metadata, facilitating model governance and deployment.

**model serving**: Infrastructure and systems that expose deployed machine learning models through APIs to handle prediction requests at scale with appropriate latency and throughput.

**model training**: The process of using machine learning algorithms to learn patterns from training data, adjusting model parameters to minimize prediction errors and create a functional predictive system.

**model uncertainty**: The inadequacy of a machine learning model to capture the full complexity of the underlying data-generating process, leading to prediction uncertainty.

**model validation**: The process of testing machine learning models on independent datasets to assess their generalization ability and ensure they perform reliably on unseen data

**model versioning**: The systematic tracking and management of different versions of machine learning models, including their parameters, training data, and performance metrics, to enable comparison and rollback capabilities

**model watermarking**: A technique for embedding verifiable ownership signatures into machine learning models that can be used to detect unauthorized use or prove intellectual property theft.

**momentum**: An optimization technique that accumulates a velocity vector across iterations to help gradient descent navigate through local minima and accelerate convergence in consistent gradient directions.

**monitoring**: The continuous observation and measurement of machine learning system performance, data quality, and operational metrics in production to detect issues and trigger maintenance actions.

**monte carlo dropout**: A technique that uses multiple forward passes with different dropout masks at inference time to estimate prediction uncertainty.

**moore's law**: The observation that the number of transistors on a microchip doubles approximately every two years while the cost of computers is halved.

**moores law**: Intel co-founder Gordon Moore's 1965 observation that transistor density doubles every 2 years, with hardware improvements following this trend while AI algorithmic efficiency improved 44× in 7 years.

**multi-agent approach**: Systems architecture where multiple AI agents collaborate, negotiate, or compete to solve complex problems, enabling division of labor and specialized expertise across different components.

**multi-head attention**: An attention mechanism that uses multiple parallel attention heads, each focusing on different aspects of the input to capture diverse types of relationships simultaneously.

**multi-layer perceptron**: A feedforward neural network with one or more hidden layers between input and output, capable of learning non-linear mappings through dense connections and activation functions.

**multicalibration**: A fairness technique ensuring that model predictions remain calibrated across intersecting subgroups, addressing complex demographic interactions.

**multilayer perceptron**: A feedforward neural network with one or more hidden layers between input and output layers, capable of learning nonlinear relationships in data.

**multimodal ai**: AI systems that can process and understand multiple types of data simultaneously, such as text, images, audio, and video, enabling more comprehensive understanding and interaction.

**mycin**: One of the first large-scale expert systems developed at Stanford in 1976 to diagnose blood infections, representing the shift toward capturing human expert knowledge in specific domains rather than pursuing general artificial intelligence.

## N

**narrow ai**: AI systems designed to excel at specific, well-defined tasks but lacking the ability to generalize across diverse problem domains, in contrast to artificial general intelligence.

**nas-generated architecture**: Neural network architectures discovered through automated Neural Architecture Search rather than manual design, often achieving better efficiency-accuracy trade-offs through exhaustive exploration of design spaces.

**network structure modification**: Architectural changes to neural networks that improve efficiency, including techniques like depthwise separable convolutions, bottleneck layers, and efficient attention mechanisms that reduce computational complexity.

**neural architecture search**: An automated approach that uses machine learning algorithms to discover optimal neural network architectures by searching through possible combinations of layers, connections, and hyperparameters for specific constraints

**neural engine**: Specialized hardware accelerators designed for machine learning inference and training, such as Apple's Neural Engine or Google's Edge TPU, optimized for on-device AI workloads.

**neural network**: A computational model consisting of interconnected nodes organized in layers that can learn to map inputs to outputs through adjustable connection weights.

**neural processing unit (npu)**: Specialized processors designed specifically for accelerating neural network operations and machine learning computations, optimized for parallel processing of AI workloads.

**neuromorphic computing**: Computing architectures inspired by the structure and function of biological neural networks, designed to process information more efficiently than traditional digital computers

**non-iid data**: Non-independent and identically distributed data where samples are not uniformly distributed across devices or time, creating challenges for federated learning convergence and generalization.

**nosql**: A category of database systems designed to handle large volumes of unstructured or semi-structured data with flexible schemas, often used in big data applications.

**numerical precision optimization**: The dimension of model optimization that addresses how numerical values are represented and processed, including quantization techniques that map high-precision values to lower-bit representations.

## O

**observability**: Comprehensive monitoring approach that provides insight into system behavior through metrics, logs, and traces, enabling understanding of internal states from external outputs.

**olap (online analytical processing)**: A database approach optimized for complex analytical queries across large datasets, typically used in data warehouses for business intelligence.

**oltp (online transaction processing)**: A database approach optimized for frequent, short transactions and real-time processing, commonly used in operational applications.

**on-chip memory**: Fast memory integrated directly onto the processor chip, including caches and scratchpad memory, providing high bandwidth and low latency data access.

**on-device learning**: The local adaptation or training of machine learning models directly on deployed hardware devices without reliance on continuous connectivity to centralized servers

**one-shot pruning**: A pruning strategy where a large fraction of parameters is removed in a single step, typically followed by fine-tuning to recover accuracy, offering simplicity but potentially requiring more aggressive fine-tuning.

**online inference**: Real-time prediction serving that processes individual requests with low latency, suitable for interactive applications requiring immediate responses.

**onnx**: Open Neural Network Exchange, a standardized format for representing machine learning models that enables interoperability between different frameworks, allowing models trained in one framework to be deployed using another.

**onnx runtime**: Cross-platform inference engine that optimizes machine learning models through techniques like operator fusion and kernel tuning to improve inference speed and reduce computational overhead.

**optimizer**: An algorithm that adjusts model parameters during training to minimize the loss function, with common examples including SGD (Stochastic Gradient Descent), Adam, and RMSprop, each with different strategies for parameter updates.

**orchestration**: The coordination and management of multiple AI systems or agents working together, ensuring proper sequencing, communication, and resource allocation across distributed intelligence systems

**outlier detection**: The process of identifying data points that significantly deviate from normal patterns, which may represent errors, anomalies, or valuable rare events.

**overfitting**: A phenomenon where a model learns specific details of training data so well that it fails to generalize to new, unseen examples, typically indicated by high training accuracy but poor validation performance.

**oxide breakdown**: The failure of an oxide layer in transistors due to excessive electric field stress, causing permanent hardware faults.

## P

**padding**: A technique in convolutional networks that adds zeros or other values around the input borders to control the spatial dimensions of the output feature maps.

**paradigm shift**: A fundamental change in scientific approach, like the shift from symbolic reasoning to statistical learning in AI during the 1990s, and from shallow to deep learning in the 2010s, requiring researchers to abandon established methods for radically different approaches.

**parallelism**: The simultaneous execution of multiple computational tasks or operations, fundamental to achieving high performance in neural network processing.

**parameter**: A learnable component of a neural network, including weights and biases, that gets adjusted during training to minimize the loss function.

**parameter efficient finetuning**: Methods like LoRA and Adapters that update less than 1% of model parameters while achieving full fine-tuning performance, reducing memory requirements from gigabytes to megabytes.

**partitioning**: A database technique that divides large datasets into smaller, manageable segments based on specific criteria to improve query performance and system scalability.

**perceptron**: The fundamental building block of neural networks, consisting of weighted inputs, a bias term, and an activation function that produces a single output.

**performance insights**: Analytical observations derived from monitoring production machine learning systems that reveal opportunities for improvement in model accuracy, system efficiency, or user experience.

**performance-efficiency scaling**: Mathematical relationships describing how computational efficiency improvements translate to performance gains across different model architectures and training regimes.

**permanent faults**: Hardware defects that persist irreversibly until repair or component replacement, consistently affecting system behavior.

**perplexity**: Measurement of how well a language model predicts text, calculated as 2^(cross-entropy loss), with lower values indicating better prediction capability.

**personalization layers**: Model components, typically the final classification layers, that are adapted locally to user-specific data while keeping shared backbone layers frozen.

**physical attack**: Direct manipulation or tampering with computing hardware to compromise the security and integrity of machine learning systems, bypassing traditional software defenses.

**pipeline jungle**: Anti-pattern where complex, interdependent data processing pipelines become difficult to maintain, debug, and modify, leading to technical debt and operational complexity.

**pipeline parallelism**: A form of model parallelism where different layers of a model are placed on different devices and data flows through them in a pipeline fashion, allowing multiple batches to be processed simultaneously.

**pooling**: A downsampling operation in convolutional networks that reduces spatial dimensions while retaining important features, commonly using max or average operations over local regions.

**positional encoding**: A method used in transformer architectures to inject information about the position of tokens in a sequence, since transformers lack inherent sequential processing.

**post-hoc explanations**: Explanation methods applied after model training that treat the model as a black box and infer reasoning patterns from input-output behavior.

**post-training quantization**: A quantization approach applied to already-trained models without modifying the training process, typically involving calibration on representative data to determine optimal quantization parameters.

**power usage effectiveness**: A metric used to determine the energy efficiency of a data center, calculated as the ratio of total facility energy consumption to IT equipment energy consumption.

**power usage effectiveness (pue)**: Metric used in data centers to measure energy efficiency, calculated as the ratio of total facility power consumption to IT equipment power consumption.

**precision**: In numerical computing, the number of bits used to represent numbers, affecting both computational accuracy and resource requirements in machine learning systems.

**precision agriculture**: The use of technology including GPS, sensors, and machine learning to optimize farming practices by precisely monitoring and managing crop inputs like water, fertilizer, and pesticides.

**prefetching**: A system optimization technique that loads data into memory before it is needed, overlapping data loading with computation to reduce idle time and improve training throughput.

**principal component analysis**: Dimensionality reduction technique that identifies the most important directions of variation in data, reducing computational complexity while preserving 90%+ of data variance.

**principle of least privilege**: A security concept where users are given the minimum access levels necessary to complete their job functions, reducing security risks.

**privacy budget**: A concept in differential privacy that represents the total amount of privacy loss allowed across all queries or computations, with each operation consuming part of this finite budget.

**privacy-preserving machine learning**: Techniques and approaches that enable machine learning while protecting the privacy of individuals whose data is used for training or inference.

**privacy-preserving techniques**: Methods designed to protect individual privacy in machine learning, including differential privacy, federated learning, and local processing.

**privacy-utility tradeoff**: The fundamental tension between preserving individual privacy and maintaining the utility of data for machine learning, requiring careful balance through techniques like differential privacy.

**problem definition**: The initial stage of machine learning development that involves clearly specifying objectives, constraints, success metrics, and operational requirements to guide all subsequent development decisions.

**programmatic logic controllers**: Industrial control systems used in manufacturing and IoT environments that can be integrated with ML models for automated decision-making in operational technology contexts.

**progressive enhancement pattern**: A design pattern that establishes baseline functionality under minimal resource conditions and incrementally incorporates advanced features as additional resources become available.

**prompt engineering**: The practice of designing and optimizing text prompts to effectively communicate with large language models and achieve desired outputs from AI systems.

**protein folding problem**: The scientific challenge of predicting the three-dimensional structure of proteins from their amino acid sequences, a problem that puzzled scientists for decades until systems like AlphaFold achieved breakthrough accuracy using deep learning approaches.

**pruning**: A model compression technique that removes unnecessary connections or neurons from neural networks to reduce model size and computational requirements without significantly impacting performance

**pseudonymization**: A privacy technique that replaces direct identifiers with artificial identifiers while maintaining the ability to trace records for analysis purposes.

**pytorch**: A deep learning framework developed by Facebook's AI Research lab that emphasizes dynamic computational graphs, eager execution, and intuitive Python integration, particularly popular for research and experimentation.

## Q

**quantization**: A model compression technique that reduces the precision of model parameters and activations from higher precision formats (like 32-bit floats) to lower precision (like 8-bit integers), significantly reducing memory usage and computational requirements

**quantization granularity**: The level at which quantization parameters are applied, ranging from per-tensor (coarsest) to per-channel or per-group (finer), with finer granularity typically preserving more accuracy but requiring more storage.

**quantization-aware training**: A training approach where quantization effects are simulated during the training process, allowing the model to adapt to reduced precision and typically achieving better accuracy than post-training quantization.

**quantum machine learning**: The intersection of quantum computing and machine learning, exploring how quantum algorithms and quantum computers can enhance or transform machine learning tasks.

**queries per second (qps)**: Performance metric that measures how many inference requests a system can process in one second, commonly used to evaluate throughput in production deployments.

**query key value**: The three components of attention mechanisms where queries determine what to look for, keys represent what is available, and values contain the actual information to be weighted and combined.

## R

**real-time processing**: The processing of data as it becomes available, with guaranteed response times that meet strict timing constraints for immediate decision-making.

**receptive field**: The region of the input that influences a particular neuron's output, determining the spatial extent of patterns that can be detected by that neuron.

**rectified linear unit**: An activation function that outputs the input if positive and zero otherwise, widely used in modern neural networks for its computational simplicity and ability to avoid vanishing gradients.

**recurrent neural network**: A type of neural network designed for sequential data processing, featuring connections that create loops allowing information to persist across time steps.

**regularization**: Techniques used to prevent overfitting in neural networks by adding constraints or penalties, including methods like dropout, weight decay, and data augmentation.

**relu**: Rectified Linear Unit activation function defined as f(x) = max(0,x) that introduces nonlinearity while maintaining computational efficiency and avoiding vanishing gradient problems.

**renewable energy**: Energy collected from renewable resources that are naturally replenished, including solar, wind, hydroelectric, geothermal, and biomass sources.

**residual connection**: A skip connection that adds the input of a layer to its output, enabling the training of very deep networks by mitigating the vanishing gradient problem.

**resnet**: Residual Network, a deep convolutional architecture that introduced skip connections, enabling the training of networks with hundreds of layers and achieving breakthrough performance.

**resource paradox**: The challenge in social impact applications where areas with the greatest needs often lack the basic infrastructure required for traditional technology deployments, requiring innovative engineering solutions.

**resource-constrained environments**: Deployment contexts with limited computational power, network bandwidth, or power availability, typically requiring specialized system design and optimization techniques.

**responsible ai**: The practice of developing and deploying AI systems in ways that are ethical, fair, transparent, and beneficial to society while minimizing potential harms and biases

**retinal fundus photographs**: Medical images of the interior surface of the eye, including the retina, optic disc, and blood vessels, commonly used for diagnosing eye diseases and training medical AI systems.

**reverse-mode differentiation**: An automatic differentiation technique that computes gradients by traversing the computational graph in reverse order, highly efficient for functions with many inputs and few outputs, making it ideal for neural network training.

**reward hacking**: The phenomenon where AI systems exploit unintended aspects of reward functions to maximize scores while violating the intended objectives.

**rlhf**: Reinforcement Learning from Human Feedback - a training method that uses human preferences to guide model behavior, enabling AI systems to better align with human values and intentions.

**rmsprop**: An adaptive learning rate optimization algorithm that maintains a moving average of squared gradients to automatically adjust learning rates for each parameter during training.

**robust ai**: The ability of artificial intelligence systems to maintain performance and reliability despite internal errors, external perturbations, and environmental changes.

**robustness**: A model's ability to maintain stable and consistent performance under input variations, environmental changes, or adversarial conditions.

**robustness metrics**: Quantitative measures for evaluating model stability under various perturbations, including adversarial accuracy, certified robustness bounds, and performance under distribution shift.

**rollback**: Process of reverting to a previous stable version of a model or system when issues are detected in production, ensuring service continuity.

**roofline analysis**: A performance modeling technique that plots operational intensity against peak performance to identify whether a system is memory-bound or compute-bound, guiding optimization efforts.

## S

**scalability**: The ability of machine learning systems to handle increasing amounts of data, users, or computational demands without significant degradation in performance or user experience

**scaling laws**: Empirical relationships that quantify the correlation between model performance and training resources, following predictable power-law relationships with model size, dataset size, and compute budget

**scan chains**: Dedicated test paths in processors that provide access to internal registers and logic for comprehensive hardware testing and fault detection.

**schema**: The structure and format definition of data that specifies data types, field names, and relationships, essential for data validation and processing consistency.

**schema evolution**: The process of modifying data schemas over time while maintaining backward compatibility and ensuring continued functionality of dependent systems and applications.

**schema-on-read**: An approach used in data lakes where data structure is defined and enforced at the time of reading rather than when storing, providing flexibility for diverse data types.

**scope 1 emissions**: Direct greenhouse gas emissions from sources owned or controlled by an organization, such as on-site fuel combustion and company vehicles.

**scope 2 emissions**: Indirect greenhouse gas emissions from the generation of purchased electricity, steam, heating, or cooling consumed by an organization.

**scope 3 emissions**: All other indirect greenhouse gas emissions that occur in an organization's value chain, including manufacturing, transportation, and end-of-life disposal.

**secure aggregation**: A cryptographic protocol that enables federated learning servers to compute aggregate model updates without accessing individual client contributions, enhancing privacy protection

**secure computation**: Cryptographic protocols that enable multiple parties to jointly compute functions over private inputs without revealing those inputs to each other.

**secure multi-party computation**: A cryptographic method that allows multiple parties to jointly compute a function over their private inputs without revealing those inputs to each other.

**segmentation maps**: Detailed annotations that classify objects at the pixel level, providing the most granular labeling information but requiring significantly more storage and processing resources.

**selective computation**: Computational strategies that dynamically allocate processing resources based on input complexity or current needs, improving efficiency by avoiding unnecessary computation.

**self supervised learning**: Training method where models create their own labels from input data structure, enabling learning from billions of unlabeled examples and revolutionizing NLP and computer vision.

**self-attention**: An attention mechanism where queries, keys, and values all come from the same sequence, allowing each position to attend to all positions including itself.

**self-refinement**: A training approach where models iteratively improve their own outputs by critiquing and refining their initial responses, enabling continuous improvement and better alignment with desired behaviors.

**self-supervised learning**: A machine learning paradigm where models learn representations from unlabeled data by predicting parts of the input from other parts, reducing dependence on manually labeled datasets.

**semi-supervised learning**: A machine learning approach that uses both labeled and unlabeled data for training, leveraging structural assumptions to improve model performance with limited labels.

**sequential neural networks**: Neural network architectures designed to process data that occurs in sequences over time, maintaining a form of memory of previous inputs to inform current decisions, essential for tasks like predicting pedestrian movement patterns.

**serverless**: Cloud computing model where infrastructure is automatically managed by the provider, allowing code execution without server management concerns.

**service level agreement (sla)**: Formal contract specifying minimum performance standards and uptime guarantees for production services, with penalties for non-compliance.

**service level objective (slo)**: Internal targets for service reliability and performance metrics such as latency, error rates, and availability that guide operational decisions.

**shadow deployment**: Testing strategy where new model versions process live traffic in parallel with production models without affecting user-facing results, enabling safe validation.

**shallow learning**: Machine learning approaches that use algorithms with limited complexity, such as support vector machines and decision trees, which require carefully engineered features but cannot automatically discover hierarchical representations like deep learning methods.

**side-channel attack**: An attack that exploits information leaked through the physical implementation of computing systems, such as power consumption, electromagnetic emissions, or timing variations.

**sigmoid**: An activation function that maps input values to a range between 0 and 1, historically popular but prone to vanishing gradient problems in deep networks.

**silent data corruption (sdc)**: Undetected errors during computation or data transfer that propagate through system layers without triggering alerts, potentially compromising results.

**simd (single instruction, multiple data)**: A parallel computing architecture that applies the same operation to multiple data elements simultaneously, effective for regular data-parallel computations.

**simt (single instruction, multiple thread)**: An extension of SIMD that enables parallel execution across multiple independent threads, each maintaining its own state and program counter.

**single-instance throughput**: Performance measurement focusing on the rate at which a single model instance can process requests, contrasting with batch throughput metrics.

**singular value decomposition**: A matrix factorization technique that decomposes a matrix into the product of three matrices, commonly used in low-rank approximations to compress neural network layers by retaining only the most significant singular values.

**skip connection**: A direct connection that bypasses one or more layers, allowing gradients to flow more easily through deep networks and enabling better training of very deep architectures.

**smallholder farmers**: Farmers operating on plots smaller than 2 hectares who produce a significant portion of global food supply but often lack access to modern agricultural technology and credit.

**social impact measurement**: Systematic evaluation of how AI applications affect communities and individuals, including metrics for accessibility, equity, effectiveness, and unintended consequences.

**softmax**: An activation function that converts raw scores into a probability distribution where outputs sum to 1, essential for multi-class classification tasks.

**software fault**: Unintended behavior in software systems resulting from defects, bugs, or design oversights that can impair performance or compromise security.

**sparse training**: A training approach that maintains sparsity in neural network weights throughout the training process, reducing computational requirements and memory usage.

**sparse updates**: A training strategy that selectively updates only a subset of model parameters based on their importance or contribution to performance, reducing computational and memory overhead.

**sparsity**: The property of neural networks where many weights are zero or near-zero, which can be exploited for computational efficiency through specialized hardware support and algorithms designed for sparse operations.

**spec cpu**: Standardized benchmark suite developed by the System Performance Evaluation Cooperative that measures processor performance using real-world applications rather than synthetic tests.

**spec power**: Benchmark methodology that measures server energy efficiency across varying workload levels, enabling direct comparisons of power-performance trade-offs in computing systems.

**specification gaming**: When AI systems find unexpected ways to achieve high rewards that technically satisfy the objective function but violate the intended purpose.

**speculative decoding**: An optimization technique for autoregressive language models where a smaller model generates draft tokens that are then verified by a larger model, accelerating inference while maintaining quality.

**speculative execution**: A performance optimization in processors that executes instructions before confirming they are needed, which can inadvertently expose sensitive data through microarchitectural side channels.

**squeezenet**: Compact CNN architecture achieving AlexNet-level accuracy with 50× fewer parameters, demonstrating that clever architecture design can dramatically reduce model size without sacrificing performance.

**stage-specific metrics**: Performance indicators tailored to individual lifecycle phases, such as data quality metrics during preparation, training convergence during modeling, and latency metrics during deployment.

**state space models**: Neural architectures that process sequences by maintaining compressed memory representations that update incrementally, offering linear scaling advantages over transformer attention mechanisms.

**static graph**: A computational graph that is defined completely before execution begins, enabling comprehensive optimization and efficient deployment but requiring all operations to be specified upfront, limiting runtime flexibility.

**static graphs vs dynamic graphs**: Two fundamental approaches to representing computations in ML frameworks: static graphs are defined before execution and enable optimization but limit flexibility, while dynamic graphs are built during execution allowing for flexible control flow but with potential optimization limitations.

**static quantization**: A quantization approach where quantization parameters are determined once during calibration and remain fixed during inference, providing computational efficiency but less adaptability than dynamic approaches.

**statistical learning**: The era of machine learning that emerged in the 1990s, shifting focus from rule-based symbolic AI to algorithms that could learn patterns from data, laying the groundwork for modern data-driven approaches to artificial intelligence.

**stochastic computing**: Computing techniques that use random bits and probabilistic operations to perform arithmetic, potentially offering better fault tolerance than traditional methods.

**stochastic gradient descent**: A variant of gradient descent that estimates gradients using individual training examples or small batches rather than the entire dataset, reducing memory requirements and enabling online learning.

**stream ingestion**: A data processing pattern that handles data in real-time as it arrives, essential for applications requiring immediate processing and low-latency responses.

**stream processing**: Real-time data processing approach that handles continuous flows of data as it arrives, enabling immediate responses to events and pattern detection.

**stride**: The step size by which a convolutional filter moves across the input, controlling the spatial dimensions of the output and the degree of overlap between filter applications.

**structured pruning**: A pruning approach that removes entire computational units such as neurons, channels, or layers, producing smaller dense models that are more hardware-friendly than the sparse matrices created by unstructured pruning.

**stuck-at fault**: A permanent hardware fault where a signal line becomes fixed at a logical 0 or 1 regardless of input, causing incorrect computations.

**student system**: One of the first AI programs from 1964 by Daniel Bobrow that demonstrated natural language understanding by converting English algebra word problems into mathematical equations, marking an important milestone in symbolic AI.

**student-teacher learning**: The core mechanism of knowledge distillation where a smaller student network learns from a larger teacher network, typically using soft targets that provide more information than hard classification labels.

**supervised learning**: A machine learning approach where models learn from labeled training examples to make predictions on new, unlabeled data.

**supply chain attack**: An attack that compromises hardware or software components during the manufacturing, distribution, or integration process, potentially affecting multiple downstream systems.

**support vector machines**: Machine learning algorithm using the "kernel trick" to find optimal decision boundaries, dominating competitions before deep learning until neural networks gained prominence around 2010.

**sustainable ai**: The practice of developing and deploying artificial intelligence systems that minimize environmental impact while maintaining effectiveness and accessibility.

**sustainable development goals**: A collection of 17 global goals adopted by the United Nations to address pressing social, economic, and environmental challenges by 2030, providing a framework for AI applications in social good.

**swarm intelligence**: Collective intelligence emerging from decentralized, self-organized systems, often inspired by biological swarms and applied to distributed ML systems and robotics.

**symbolic ai**: The early approach to artificial intelligence that attempted to implement intelligence through symbol manipulation and rule-based systems, exemplified by programs like STUDENT that could only handle inputs matching their pre-programmed patterns

**symbolic programming**: A programming paradigm where computations are represented as abstract symbols and expressions that are constructed first and executed later, allowing for comprehensive optimization but requiring explicit execution phases.

**synthetic benchmark**: Artificial test program designed to measure specific aspects of system performance, as opposed to benchmarks based on real-world applications and workloads.

**synthetic data**: Artificially generated data created using algorithms, simulations, or generative models to supplement real-world datasets, addressing limitations in data availability or privacy concerns.

**synthetic data generation**: The creation of artificial datasets that approximate the statistical properties of real data while reducing privacy risks and avoiding direct exposure of sensitive information.

**system efficiency**: Optimization of machine learning systems across algorithmic, compute, and data efficiency dimensions to minimize computational, memory, and energy demands while maintaining performance.

**system on chip**: An integrated circuit that incorporates most or all components of a computer or electronic system, including CPU, GPU, memory, and specialized processors on a single chip.

**system-on-chip (soc)**: Integrated circuit that contains most or all components of a computer system, commonly used in mobile devices and embedded systems for space and power efficiency.

**system-wide sustainability**: Holistic approach to environmental responsibility that considers the entire AI infrastructure ecosystem, from data centers to edge devices, rather than optimizing individual components in isolation.

**systems integration**: The process of combining various components and subsystems into a unified, functional system that operates efficiently and reliably as a whole.

**systems thinking**: An approach to understanding complex systems by considering how individual components interact and affect the whole system, particularly important in ML where data, algorithms, hardware, and deployment environments must work together effectively

**systolic array**: A specialized hardware architecture that efficiently performs matrix operations by streaming data through a grid of processing elements, minimized data movement and energy consumption.

## T

**tail latency**: Worst-case response times in a system, typically measured as 95th or 99th percentile latency, important for understanding system reliability under peak load conditions.

**tailored inference benchmarks**: Specialized performance tests designed for specific deployment environments or use cases, accounting for unique constraints and optimization requirements.

**tanh**: An activation function that maps inputs to the range (-1,1) with zero-centered output, helping to stabilize gradient-based optimization compared to sigmoid functions.

**targeted attack**: A type of data poisoning attack that aims to cause misclassification of specific inputs or classes while leaving the model's general performance largely intact.

**technical debt**: Long-term maintenance cost accumulated from expedient design decisions during development, particularly problematic in ML systems due to data dependencies and model complexity.

**telemetry**: Automated collection and transmission of performance data and metrics from distributed systems, enabling remote monitoring and analysis.

**tensor**: A multi-dimensional array used to represent data in neural networks, generalizing scalars (0D), vectors (1D), and matrices (2D) to higher dimensions.

**tensor decomposition**: The extension of matrix factorization to higher-order tensors, used to compress neural network layers by representing weight tensors as combinations of smaller tensors with fewer parameters.

**tensor parallelism**: A distributed computing technique that partitions individual tensors and operations across multiple devices, reducing per-device memory requirements while maintaining computational efficiency through coordinated parallel execution.

**tensor processing unit**: Google's custom application-specific integrated circuit designed specifically for machine learning workloads, optimized for matrix operations and featuring systolic array architecture.

**tensor processing unit (tpu)**: Google's custom application-specific integrated circuit designed specifically for neural network machine learning, optimized for TensorFlow operations.

**tensorflow**: A comprehensive machine learning framework developed by Google that provides tools for the entire ML pipeline from research to production, featuring both eager execution and graph-based computation with extensive ecosystem support.

**tensorrt**: NVIDIA's inference optimization library that applies techniques like operator fusion and precision reduction to accelerate deep learning inference on GPU hardware.

**ternarization**: An extreme quantization technique that constrains weights to three values (typically -1, 0, +1), providing significant compression while maintaining more representational capacity than binary quantization.

**test time compute**: Dynamic resource allocation during inference that adjusts computational effort based on task complexity or importance, enabling flexible performance-accuracy trade-offs.

**thermal stress**: Hardware degradation caused by repeated cycling through high and low temperatures, leading to material fatigue and potential failures.

**threshold for activation**: The input level at which a neuron begins to produce significant output, determined by the combination of weights, biases, and the chosen activation function, controlling when the neuron contributes to the network's computation.

**throughput**: The rate at which a system can process data or complete operations, typically measured in operations per second and crucial for training large models

**time-to-accuracy**: Duration required for a machine learning model to reach a predefined accuracy threshold during training, serving as a key metric for training efficiency evaluation.

**tiny machine learning**: The execution of machine learning models on ultra-constrained devices such as microcontrollers and sensors, operating in the milliwatt to sub-watt power range.

**tiny ml**: Machine learning systems designed to run on extremely resource-constrained devices like microcontrollers, typically with models under 1 MB and power consumption under 150 mW.

**tinyml**: Machine learning on microcontrollers and edge devices with less than 1KB-1MB memory and less than 1mW power consumption, enabling AI in IoT devices where traditional deployment is impossible

**tokens**: Individual units of text that language models process, typically words or subword pieces, with modern models like GPT-3 trained on hundreds of billions of tokens.

**tops**: Tera Operations Per Second, a measure of computational performance indicating how many trillion operations a system can execute in one second.

**tpu**: Tensor Processing Unit, Google's custom Application-Specific Integrated Circuits (ASICs) designed specifically for accelerating tensor operations in machine learning workloads, offering significant performance and energy efficiency improvements over general-purpose processors

**training**: The process of adjusting neural network parameters using labeled data and optimization algorithms to minimize prediction errors and improve performance.

**training-serving skew**: Inconsistency between feature preprocessing logic used during model training versus serving, leading to degraded production performance.

**transfer learning**: A machine learning technique that leverages knowledge gained from pre-trained models on related tasks, allowing faster training and better performance on new tasks with limited data by reusing learned features and representations

**transformer**: A neural network architecture based entirely on attention mechanisms, eliminating recurrence and convolution while achieving state-of-the-art performance across many domains.

**transformer architecture**: A neural network architecture based on attention mechanisms that has revolutionized natural language processing and is increasingly applied to other domains like computer vision.

**transient faults**: Temporary hardware faults that do not persist or cause permanent damage but can lead to incorrect computations if not handled properly.

**translation invariance**: The property of convolutional networks to recognize patterns regardless of their position in the input, achieved through weight sharing and pooling operations.

**transparency**: Openness about how AI systems are built, trained, validated, and deployed, including disclosure of data sources, design assumptions, and limitations.

**triple modular redundancy (tmr)**: A fault-tolerance technique where three instances of a computation are performed, with majority voting determining the correct result.

**trusted execution environment**: A secure area within a processor that provides hardware-based protection for code and data, ensuring confidentiality and integrity even from privileged system software.

**tucker decomposition**: A tensor decomposition method that generalizes singular value decomposition to higher-order tensors using a core tensor and factor matrices, commonly used for compressing convolutional neural network layers.

**tv white spaces**: Unused broadcasting frequencies that can be repurposed for internet connectivity, as employed by systems like FarmBeats to extend network access to remote agricultural sensors and IoT devices.

## U

**uci machine learning repository**: Established in 1987 by the University of California Irvine, one of the most widely-used resources for machine learning datasets containing over 600 datasets cited in thousands of research papers.

**uniform quantization**: A quantization approach where the range of values is divided into evenly spaced intervals, providing simple implementation but potentially suboptimal for non-uniform value distributions.

**universal approximation theorem**: A theoretical result proving that neural networks with sufficient width and non-linear activation functions can approximate any continuous function on a compact domain.

**unstructured pruning**: A pruning approach that removes individual weights while preserving the overall network architecture, creating sparse weight matrices that require specialized hardware support to realize computational benefits.

**unstructured sparsity**: A form of model sparsity where individual weights are set to zero without following any particular pattern, creating irregular sparsity patterns that require specialized hardware support to realize computational benefits.

## V

**validation issues**: Problems identified during model testing that indicate poor performance, overfitting, data quality problems, or other issues that must be resolved before deployment.

**value alignment**: The principle that AI systems should pursue goals consistent with human intent and ethical norms, addressing the challenge of encoding human values in machine objectives.

**value-sensitive design**: A methodology for incorporating human values into technology design through systematic stakeholder engagement and ethical consideration of system impacts.

**vanishing gradient**: A problem in deep neural networks where gradients become exponentially smaller as they propagate backward through layers, making it difficult for early layers to learn effectively.

**vanishing gradient problem**: A challenge in training deep neural networks where gradients become exponentially smaller as they propagate backward through layers, making it difficult to train early layers effectively.

**vector operations**: Computational operations that process multiple data elements simultaneously, enabling efficient parallel execution of element-wise transformations in neural networks.

**vector-borne diseases**: Diseases transmitted by insects or other vectors, such as malaria carried by mosquitoes, which can be monitored and controlled using machine learning-powered detection systems.

**versioning**: The practice of tracking changes to datasets, models, and pipelines over time, enabling reproducibility, rollback capabilities, and audit trails in ML systems.

**virtuous cycle**: The self-reinforcing process in deep learning where improvements in data availability, algorithms, and computing power each enable further advances in the other areas, accelerating overall progress.

**vision-language models**: AI systems that can understand and reason about both visual and textual information simultaneously, enabling tasks like image captioning, visual question answering, and multimodal understanding.

**von neumann bottleneck**: The performance limitation caused by the shared bus between processor and memory in traditional computer architectures, where data movement becomes more expensive than computation.

## W

**watchdog timer**: A hardware component that monitors system execution and triggers recovery actions if the system becomes unresponsive or stuck.

**water usage effectiveness**: A metric that measures the efficiency of water use in data centers, calculated as the ratio of total water consumed to IT equipment energy consumption.

**waymo**: A subsidiary of Alphabet Inc. that represents one of the most ambitious applications of machine learning systems in autonomous vehicle technology, demonstrating how ML systems can span from embedded systems to cloud infrastructure in safety-critical environments.

**weak supervision**: An approach that uses lower-quality labels obtained more efficiently through heuristics, distant supervision, or programmatic methods rather than manual expert annotation.

**web scraping**: An automated technique for extracting data from websites to build custom datasets, requiring careful consideration of legal, ethical, and technical constraints.

**weight**: A learnable parameter that determines the strength of connection between neurons in different layers, adjusted during training to minimize the loss function.

**weight freezing**: A technique that fixes most model parameters during training while allowing only specific layers or components to be updated, reducing computational requirements for on-device adaptation.

**weight matrix**: An organized collection of weights connecting one layer to another in a neural network, enabling efficient computation through matrix operations.

**weight sharing**: The practice of using the same parameters across different spatial locations, as in convolutional networks, reducing the number of parameters while maintaining pattern detection capabilities.

**whetstone**: Early benchmark introduced in 1964 that measured floating-point arithmetic performance in KIPS (thousands of instructions per second), becoming the first widely-adopted standardized performance test.

**white-box attack**: An adversarial attack where the attacker has complete knowledge of the model's architecture, parameters, training data, and internal workings, enabling highly effective attack strategies.

**workflow orchestration**: Automated coordination and management of complex ML pipeline sequences, ensuring proper execution order, dependency management, and error handling across distributed systems.

## X

**xla**: Accelerated Linear Algebra, a domain-specific compiler for linear algebra operations that optimizes TensorFlow and JAX computations by generating efficient code for various hardware platforms including CPUs, GPUs, and TPUs.

## Z

**zero-day vulnerability**: A previously unknown security flaw in software or hardware that can be exploited by attackers before developers have had a chance to create and distribute a patch.

**zero-shot learning**: The ability of machine learning models to perform tasks or classify objects they have never seen during training, often achieved through sophisticated representation learning or large-scale pre-training.


## Related Concepts

- [[benchmarking]]
- [[hw_acceleration]]
- [[dnn_architectures]]
- [[frameworks]]
- [[responsible_ai]]
- [[sustainable_ai]]
- [[ml_systems]]
- [[ai_for_good]]
