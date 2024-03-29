# featureExtractorCCA.py
"""
Feature extraction method using correlation coefficient analysis.
Chen, Xiaogang, et al. "Filter bank canonical correlation analysis
for implementing a high-speed SSVEP-based brain–computer interface.
Journal of neural engineering 12.4 (2015): 046008.
"""

# Import the definition of the parent class.  Make sure the file is in the
# working directory. 
from .featureExtractorTemplateMatching \
    import FeatureExtractorTemplateMatching

# Needed for basic matrix operations. 
import numpy as np

try:
    import cupy as cp
    cupy_available_global = True
except:
    cupy_available_global = False
    cp = np

class FeatureExtractorCCA(FeatureExtractorTemplateMatching):
    """Implementation of feature extraction using CCA"""
    
    def __init__(self):
        "Class constructor"            
        super().__init__()

        # If set to True, the feature extraction method only returns
        # the maximum correlation coefficient.  Otherwise, the class
        # returns k correlation coefficients, where k is the minimum of
        # of the template signal rank and signal rank.  Most studies use
        # only the maximum.  Thus, the default value is True. 
        self.max_correlation_only = True
     
    def setup_feature_extractor(
            self, 
            harmonics_count,
            targets_frequencies,
            sampling_frequency,
            subbands=None,
            max_correlation_only=True,
            embedding_dimension=0,
            delay_step=0,
            filter_order=0,
            filter_cutoff_low=0,
            filter_cutoff_high=0,
            voters_count=1,
            random_seed=0,
            use_gpu=False,
            max_batch_size=16,
            explicit_multithreading=0,
            samples_count=0):
        """
        Setup the feature extractor parameters CCA.
        
        Mandatory Parameters:
        -------------------------------------
        harmonics_count: The number of harmonics to be used in constructing
        the template signal.  This variable must be a positive integer 
        number (typically a value from 3 to 5).  
        
        targets_frequencies: The stimulation freqeuency of each target.  
        This must be a 1D array,  where the first element is the stimulation
        frequency of the first target, the second element is the stimulation
        frequency of the second target, and so on.  The length of this array
        indicates the number of targets.  The user must determine the 
        targets_frequencies but the number of targets (targets_count) is 
        extracted automatically from the length of targets_frequencies. 
        
        sampling_frequency: The sampling rate of the signal 
        (in samples per second).  It must be a real positive value. 
                
        Optional Parameters:
        --------------------        
        embedding_dimension: This is the dimension of time-delay embedding. 
        This must be a non-negative integer.  If set to zero, no time-delay
        embedding will be used.  If there are E electrodes and we set the 
        embedding_dimension to n, the class expands the input signal as if we
        had n*E channels.  The additional channels are generated by shift_left
        operator. The number of samples that we shift each signal is 
        controlled by delay_step.  Embedding delays truncates the signal. 
        Make sure the signal is long enough. 
        
        delay_step: The number of samples that are shifted for each delay
        embedding dimension.  For example, assume we have ten channels, 
        embedding_dimension is two, and delay_step is three.  In this case, the
        class creates 30 channels.  The first ten channels are the original
        signals coming from the ten electrodes.  The second ten signals are
        obtained by shifting the origianl signals by three samples.  The third
        ten signals are obtained by shifting the original signals by six 
        samples.  The signals are truncated accordingly. 
        
        filter_order: The order of the filter used for filtering signals before
        analysis.  If filter_order is zero (the default value), no filtering
        is performed.  Otherwise, the class creates a filter of order 
        filter_order.  This must be positive integer. 
        
        cutoff_frequency_low: The first cutoff frequency of the bandpass 
        filter.  This must be a single real positive number.  If filter_order
        is zero, this attribute is ignored.  
        
        cutoff_frequency_high: The second cutoff frequency of the bandpass
        filter. This must be a single real positive number.  If filter_order
        is zero, this attribute is ignored.  
        
        subbands: This is the primary way to instruct the classifier whether 
        to use filterbank or not.  The default value is None.  If set to None, 
        the classifier uses none-fitlerbank implementation.  To use
        filterbanks, subbands must be set to a 2D array, whith exactly two 
        columns.  Each row of this matrix defines a subband with two 
        frequencies provided in two columns.  The first column is the first
        cutoff frequency and the second column is the second cutoff frequency
        of that subband.  Filterbank filters the signal using a bandpass
        filter with these cutoff frequencies to obtain a new subband.  The
        number of rows in the matrix defines the number of subbands. All
        frequencies must be in Hz.  For each row, the second column must
        always be greater than the first column. 
        
        voters_count: The number of electrode-selections that are used for
        classification.  This must be a positive integer.  This is the 
        same as the number of voters.  If voters_count is larger that the 
        cardinality of the power set of the current selected electrodes, 
        then at least one combination is bound to happen more than once. 
        However, because the selection is random, even if voters_count is
        less than the cardinality of the power set, repettitions are still
        possible (although unlikely). If not specified or set to 1, no 
        voting will be used. 
        
        random_seed: This parameter control the seed for random selection 
        of electrodes.  This must be set to a non-negative integer.  The 
        default value is zero.
                
        use_gpu: When set to 'True,' the class uses a gpu to extract features.
        The host must be equipped with a CUDA-capable GPU.  When set to
        'False,' all processing will be on CPU. 
        
        max_batch_size: The maximum number of signals/channel selections
        that are processed in one batch.  Increasing this number improves
        parallelization at the expense of more memory requirement.  
        This must be a single positve integer. 
        
        explicit_multithreading: This parameter determines whether to use 
        explicit multithreading or not.  If set to a non-positive integer, 
        no multithreading will be used.  If set to a positive integer, the 
        class creates multiple threads to process signals/voters in paralle.
        The number of threads is the same as the value of this variable. 
        E.g., if set to 4, the class distributes the workload among four 
        threads.  Typically, this parameter should be the same as the number
        of cores the cput has, if multithreading is to be used. 
        Multithreading cannot be used when use_gpu is set to True.
        If multithreading is set to a positive value while used_gpu is 
        set to True or vice versa, the classes raises an error and the 
        program terminates. 
        
        samples_count: If provided, the class performs precomputations that
        only depend on the number of samples, e.g., computing the template
        signal.  If not provided, the class does not perform precomputations.
        Instead, it does the computations once the input signal was provided 
        and the class learns the number of samples from the input signal. 
        Setting samples_count is highly recommended.  If the feaure extraction
        method is being used in loop (e.g., BCI2000 loop), setting this 
        parameter eliminates the need to compute the template matrix each
        time. It also helps the class to avoid other computations in each
        iteration. samples_count passed to this function must be the same 
        as the third dimension size of the signal passed to extract_features().
        If that is not the case, the template and input signal will have 
        different dimensions.  The class should issue an error in this case
        and terminate the execution. 
        """        
        self.build_feature_extractor(
            harmonics_count,
            targets_frequencies,
            sampling_frequency,
            subbands=subbands,           
            embedding_dimension=embedding_dimension,
            delay_step=delay_step,
            filter_order=filter_order,
            filter_cutoff_low=filter_cutoff_low,
            filter_cutoff_high=filter_cutoff_high,
            voters_count=voters_count,
            random_seed=random_seed,
            use_gpu=use_gpu,
            max_batch_size=max_batch_size,
            explicit_multithreading=explicit_multithreading,
            samples_count=samples_count)
            
        self.max_correlation_only = max_correlation_only
                        
    def get_features(self, device):
        """Extract features using CCA"""   
        # Get the current batch of data        
        signal = self.get_current_data_batch()        
        correlations = self.canonical_correlation_reduced(signal, device)  
        xp = self.get_array_module(correlations)
        
        if self.max_correlation_only == True:
            correlations = xp.max(correlations, axis=-1)
                   
        batch_size = self.channel_selection_info_bundle[1]
        signals_count = correlations.shape[0]//batch_size
        
        # De-bundle the results.
        correlations = xp.reshape(correlations, (
            signals_count,
            batch_size,
            self.targets_count,            
            -1))
        
        if self.max_correlation_only == True:
            features = correlations
        
        else:                
            # De-bundle the results.
            features = xp.zeros((
                signals_count,
                batch_size,
                self.targets_count,
                self.features_count),
                dtype=np.float32)
        
            features[:, :, :, :correlations.shape[-1]] = correlations
        
        return features
    
    def get_features_multithreaded(self, signal):
        """Extract MSI features from a single signal"""        
        # Make sure signal is 3D
        signal -= np.mean(signal, axis=-1)[:, None]
        signal = signal[None, :, :] 
            
        if self.max_correlation_only == False:
            self.features_count = np.min((
                self.electrodes_count, 2*self.harmonics_count))
            
        correlations = self.canonical_correlation_reduced(signal, device=0)  

        if self.max_correlation_only == True:
            correlations = np.max(correlations, axis=-1)
                       
        # De-bundle the results.
        correlations = np.reshape(correlations, (
            1, 
            1,
            1,
            self.targets_count,            
            -1))
        
        if self.max_correlation_only == True:
            features = correlations
        
        else:                
            # De-bundle the results.
            features = np.zeros((
                1, 
                1,
                1,
                self.targets_count,               
                self.features_count),
                dtype=np.float32)
        
            features[:, :, :, :, :correlations.shape[-1]] = correlations
        
        return features
        
    def canonical_correlation_reduced(self, signal, device):
        """Compute the canonical correlation between X and Y. """         
        q_template = self.q_template_handle[device]
        xp = self.get_array_module(q_template)    
         
        signal = xp.transpose(signal, axes=(0, 2, 1))      
        
        # q_signal = xp.linalg.qr(signal[0])[0]
        # q_signal = xp.expand_dims(q_signal, axis=0)

        if self.explicit_multithreading > 0:
            q_signal = np.linalg.qr(signal[0])[0]
            q_signal = np.expand_dims(q_signal, axis=0)
        else:   
            q_signal = xp.linalg.qr(signal)[0]
            # q_signal = xp.expand_dims(q_signal, axis=0)
            # q_signal = self.qr_decomposition(signal)
        q_signal = xp.transpose(q_signal, axes=(0, 2, 1))
                     
        product = xp.matmul(
            q_signal[:, None, :, :], q_template[None, :, :, :])
        
        r = xp.linalg.svd(product, full_matrices=False, compute_uv=False)
        r[r>1] = 1
        r[r<0] = 0
        
        return r
    
    def qr_decomposition(self, X):
        """QR Decomposition based on Schwarz Rutishauser algorithm"""
        # Credit: Arthur V. Ratz (towardsdatascience.com)
        # Current implementation is slow on GPU.
        # Because we launch too many small kernels.
        xp = self.get_array_module(X)
        Q = X
        ns, m, n = X.shape
        R = xp.zeros((ns, n, n), dtype=xp.float32)
        
        for k in xp.arange(n):
            for i in xp.arange(k):
                Qt = Q[:, :, i]
                R[:, i, k] = xp.sum(xp.multiply(Qt, Q[:, :, k]), axis=1)
                product = xp.multiply(R[:, i, k][:, None], Q[:, :, i])
                Q[:, :, k] = Q[:, :, k] - product
                
            R[:, k, k] = xp.sum(xp.square(Q[:, :, k]), axis=-1)
            R[:, k, k] = xp.sqrt(R[:, k, k])
            Q[:, :, k] = xp.divide(Q[:, :, k], R[:, k, k][:, None])
            
        return -Q
                
    def perform_voting_initialization(self, device=0):
        """Perform initialization and precomputations common to all voters"""
        # Center data
        self.all_signals -= np.mean(self.all_signals, axis=-1)[:, :, None]     
        self.all_signals_handle = self.handle_generator(self.all_signals)
        rank = np.linalg.matrix_rank(self.all_signals)
        
        if any(rank < np.min(self.all_signals.shape[1:])):
            self.quit("Input signal is not full rank!  ")         
            
        if self.max_correlation_only == False:
            self.features_count = np.min((
                self.electrodes_count, 2*self.harmonics_count))
        
    def class_specific_initializations(self):
        """Perform necessary initializations"""
        # Perform some percomputations only in the first run.  
        # These computations only rely on the template signal and can thus
        # be pre-computed to improve performance. 
        self.compute_templates()  
        
        if self.samples_count == 1:
            self.quit("Signal is too short. Cannot compute canoncial "
                      + "correlations of a matrix with a single sample.")
            
        # Center the template signal. It should be already pretty much 
        # centered by if the cut-off does not align well with the end 
        # of period, we might get some non-zero weights. 
        self.template_signal -= np.mean(
            self.template_signal, axis=1)[:, None, :]
        
        # Q part of the QR decomposition
        self.q_template = np.zeros(
            self.template_signal.shape, dtype=np.float32)
        
        for i in np.arange(self.targets_count):        
            self.q_template[i] = np.linalg.qr(self.template_signal[i])[0]
            
        rank_template = np.linalg.matrix_rank(self.template_signal)
        
        if any(rank_template != 2*self.harmonics_count):
            self.quit("Template matrix is not full rank.")
         
        self.template_signal_handle = self.handle_generator(
            self.template_signal)
        
        self.q_template_handle = self.handle_generator(
            self.q_template)
               
    def get_current_data_batch(self):
        """Bundle all data so they can be processed toegher"""
        # Bundling helps increase GPU and CPU utilization. 
       
        # Extract bundle information. 
        # Helps with the code's readability. 
        batch_index = self.channel_selection_info_bundle[0]        
        batch_population = self.channel_selection_info_bundle[1]
        batch_electrodes_count = self.channel_selection_info_bundle[2]
        first_signal = self.channel_selection_info_bundle[3]
        last_signal = self.channel_selection_info_bundle[4]
        signals_count = last_signal - first_signal
        
        # Pre-allocate memory for the batch
        signal = np.zeros(
            (signals_count, batch_population,
             batch_electrodes_count, self.samples_count),
            dtype=np.float32)        
        
        selected_signals = self.all_signals_handle[0][first_signal:last_signal]
        
        for j in np.arange(batch_population):
            current_selection = self.channel_selections[batch_index]
            signal[:, j] = selected_signals[:, current_selection, :]
            batch_index += 1
                        
        signal = np.reshape(signal, (-1,) + signal.shape[2:])
          
        # Move the extracted batches to the device memory if need be. 
        if self.use_gpu == True:          
            signal = cp.asarray(signal)
            
        return signal
        
    @property
    def max_correlation_only(self):
        """Getter for max_correlation_only flag"""
        return self.__max_correlation_only
    
    @max_correlation_only.setter
    def max_correlation_only(self, flag):
        """Setter for max_correlation_only flag"""
        try:
            flag = bool(flag)
        except(ValueError, TypeError):
            self.quit("max_correlation_only flag must be Boolean.")
            
        self.__max_correlation_only = flag
        