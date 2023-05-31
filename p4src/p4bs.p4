/* -*- P4_16 -*- */

#include <core.p4>
#include <tna.p4>

/*************************************************************************
 ************* C O N S T A N T S    A N D   T Y P E S  *******************
**************************************************************************/
const bit<16> ETHERTYPE_TPID = 0x8100;
const bit<16> ETHERTYPE_IPV4 = 0x0800;
typedef bit<32> value_t;

#define SKETCH_BUCKET_LENGTH  131072 //65535 //8192 
#define SKETCH_CELL_BIT_WIDTH 16
#define THRESH 100000

#define SKETCH_REGISTER(num) Register<bit<SKETCH_CELL_BIT_WIDTH>, _>(SKETCH_BUCKET_LENGTH) sketch##num



#define SKETCH_COUNT(num, algorithm, crc) Hash<bit<17>>(algorithm, crc) hash##num; \
action apply_hash_##num() { \
    meta.index_sketch##num = hash##num.get({ \
        hdr.ipv4.src_addr, \
        hdr.ipv4.dst_addr, \
        hdr.ipv4.protocol, \
        hdr.tcp.src_port, \
        hdr.tcp.dst_port \
    }); \
}\
RegisterAction<bit<SKETCH_CELL_BIT_WIDTH>, _, bit<1>>(sketch##num) read_sketch##num = {\
    void apply(inout bit<SKETCH_CELL_BIT_WIDTH> register_data, out bit<1> result) { \
        register_data = register_data +1; \
        if (register_data > THRESH) {\
            result = 1; \
        } else {\
            result = 0; \
        }\
    } \
}; \
action exec_read_sketch##num() { \
    meta.value_sketch##num = read_sketch##num.execute(meta.index_sketch##num); \
} 


/*************************************************************************
 ***********************  H E A D E R S  *********************************
 *************************************************************************/

/*  Define all the headers the program will recognize             */
/*  The actual sets of headers processed by each gress cn differ */

/* Standard ethernet header */
header ethernet_h {
    bit<48>   dst_addr;
    bit<48>   src_addr;
    bit<16>   ether_type;
}

header vlan_tag_h {
    bit<3>   pcp;
    bit<1>   cfi;
    bit<12>  vid;
    bit<16>  ether_type;
}

header ipv4_h {
    bit<4>   version;
    bit<4>   ihl;
    bit<8>   diffserv;
    bit<16>  total_len;
    bit<16>  identification;
    bit<3>   flags;
    bit<13>  frag_offset;
    bit<8>   ttl;
    bit<8>   protocol;
    bit<16>  hdr_checksum;
    bit<32>  src_addr;
    bit<32>  dst_addr;
}

header tcp_h {
    bit<16> src_port;
    bit<16> dst_port;
    bit<32> seq_no;
    bit<32> ack_no;
    bit<4> data_offset;
    bit<4> res;
    bit<8> flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgent_ptr;
	bit<9> in_port;
	bit<7> dummy;
}

header udp_h {
	bit<16> src_port;
    bit<16> dst_port;
    bit<16> hdr_length;
    bit<16> checksum;
}

header rtp_h {
    bit<2>   version;
    bit<1>   padding;
    bit<1>   extension;
    bit<4>   CSRC_count;
    bit<1>   marker;
    bit<7>   payload_type;
    bit<16>  sequence_number;
    bit<32>  timestamp;
    bit<32>  SSRC;
} 



struct flow_digest_t {
    bit<16> flow_id;
	bit<16> rev_flow_id;	
}  

struct RTT_digest_t {
    bit<16> flow_id; 
    bit<32> rtt;
}  

struct test_SEQ_t {
    bit<32> seq_no; 
    bit<32> expected_ack;
}  

struct queue_delay_sample_digest_t {
    bit<32> queue_delay_sample; 
}

struct before_after_t {
    bit<32> before;
    bit<32> after;	
}

struct paired_32bit {
    bit<32> lo;
    bit<32> hi;
}
#define PKT_TYPE_SEQ true
#define PKT_TYPE_ACK false
typedef bit<8> tcp_flags_t;
const tcp_flags_t TCP_FLAGS_F = 1;
const tcp_flags_t TCP_FLAGS_S = 2;
const tcp_flags_t TCP_FLAGS_R = 4;
const tcp_flags_t TCP_FLAGS_P = 8;
const tcp_flags_t TCP_FLAGS_A = 16;

/*************************************************************************
 **************  I N G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

    /***********************  H E A D E R S  ************************/

struct my_ingress_headers_t {
    ethernet_h   ethernet;
    ipv4_h       ipv4;
    tcp_h        tcp;
    udp_h        udp;
    rtp_h        rtp;

}

    /******  G L O B A L   I N G R E S S   M E T A D A T A  *********/
    struct my_ingress_metadata_t {
        bit<16> flow_id;
		bit<16> rev_flow_id;
		
        bool pkt_type;
    
        bit<32> tmp_1;
        bit<32> tmp_2;
        bit<32> tmp_3;
        bit<32> total_hdr_len_bytes; 
        bit<32> total_body_len_bytes; 

		bit<32> total_before;
		bit<32> total_after;

        bit<32> expected_ack;
        bit<32> pkt_signature;

        bit<16> hashed_location_1;
        bit<16> hashed_location_2;

        bit<32> table_1_read;
        bit<32> rtt;
        bit<32> lost;
		
		bit<8> lock;
		bit<32> seq_hash;
		
		bit<9> in_port;
		
		bit<32> report_loss;
		
		bit<17> index_sketch0;
		bit<17> index_sketch1;
		bit<17> index_sketch2;
		bit<17> index_sketch3;


		bit<1> value_sketch0;
		bit<1> value_sketch1;
		bit<1> value_sketch2;
		bit<1> value_sketch3;

    }


    /***********************  P A R S E R  **************************/
parser IngressParser(packet_in        pkt,
    /* User */
    out my_ingress_headers_t          hdr,
    out my_ingress_metadata_t         meta,
    /* Intrinsic */
    out ingress_intrinsic_metadata_t  ig_intr_md)
{
    /* This is a mandatory state, required by Tofino Architecture */
    state start {
        pkt.extract(ig_intr_md);
        pkt.advance(PORT_METADATA_SIZE);
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4:  parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            6: parse_tcp;
            0x11: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        pkt.extract(hdr.tcp);
        transition accept;
    }

    state parse_udp {
        pkt.extract(hdr.udp);
        transition parse_rtp;
    }
	
	state parse_rtp {
        pkt.extract(hdr.rtp);
        transition accept;
    }


}

    /***************** M A T C H - A C T I O N  *********************/

control Ingress(
    /* User */
    inout my_ingress_headers_t                       hdr,
    inout my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_t               ig_intr_md,
    in    ingress_intrinsic_metadata_from_parser_t   ig_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t        ig_tm_md)
{

    Counter<bit<64>, bit<1>>(1, CounterType_t.BYTES) link_stats;

    DirectMeter(MeterType_t.BYTES)      bytes_meter;
    bit<2> color;
    bit<1> stored;

    Register<bit<1>, bit<16>>(65535) informed_long_flows;
    RegisterAction<bit<1>, bit<16>, bit<1>>(informed_long_flows) read_store_long_flow = {
        void apply(inout bit<1> register_data, out bit<1> result) {
             result = register_data;
             //register_data = 1;
        }
    };

    action apply_read_store_long_flow() {
        stored = read_store_long_flow.execute(meta.flow_id);
    }

    RegisterAction<bit<1>, bit<16>, bit<1>>(informed_long_flows) read_long_flow = {
        void apply(inout bit<1> register_data, out bit<1> result) {
             result = register_data;
             register_data = 0;
        }
    };

    action apply_read_long_flow() {
        stored = read_long_flow.execute(meta.flow_id);
    }
    
    // ***********************************************************************************************
    // *************************        H  A S H I N G       *****************************************
    // ***********************************************************************************************
    Hash<bit<16>>(HashAlgorithm_t.CRC16) hash;
    action apply_hash() {
        meta.flow_id = hash.get({
            hdr.ipv4.src_addr,
            hdr.ipv4.dst_addr,
            hdr.ipv4.protocol,
            hdr.tcp.src_port,
            hdr.tcp.dst_port
        });
    }
    table calc_flow_id {
        actions = {
            apply_hash;
        }
        const default_action = apply_hash();
    }
	
	SKETCH_REGISTER(0);
    SKETCH_REGISTER(1);
    SKETCH_REGISTER(2);
    SKETCH_REGISTER(3);

    CRCPolynomial<bit<17>>( 0x04C11DB7, true, false, false, 17w0xFFFF, 17w0xFFFF) crc10d_1; 
    CRCPolynomial<bit<17>>( 0xEDB88320, true, false, false, 17w0xFFFF, 17w0xFFFF) crc10d_2; 
    CRCPolynomial<bit<17>>( 0x1A83398B, true, false, false, 17w0xFFFF, 17w0xFFFF) crc10d_3; 
    CRCPolynomial<bit<17>>( 0xabc14281, true, false, false, 17w0xFFFF, 17w0xFFFF) crc10d_4; 

    SKETCH_COUNT(0, HashAlgorithm_t.CUSTOM, crc10d_1)
    SKETCH_COUNT(1, HashAlgorithm_t.CUSTOM, crc10d_2)
    SKETCH_COUNT(2, HashAlgorithm_t.CUSTOM, crc10d_3)
    SKETCH_COUNT(3, HashAlgorithm_t.CUSTOM, crc10d_4)
	
	action meter(){
    }
	table counted_flow {
        key = {
            meta.flow_id: exact;
        }
        actions = {
            meter;
            NoAction;
        }
        size = 65535;
	    const default_action = NoAction;
        idle_timeout = true;
    }
	
	Hash<bit<16>>(HashAlgorithm_t.CRC16) rev_hash;
    action apply_rev_hash() {
        meta.rev_flow_id = rev_hash.get({
            hdr.ipv4.dst_addr,
            hdr.ipv4.src_addr,
            hdr.ipv4.protocol,
            hdr.tcp.dst_port,
            hdr.tcp.src_port
        });
    }
    table calc_rev_flow_id {
        actions = {
            apply_rev_hash;
        }
        const default_action = apply_rev_hash();
    }
    // ***********************************************************************************************
    // *************************     E N D   H  A S H I N G       ************************************
    // ***********************************************************************************************




    // ***********************************************************************************************
    // *************************     R T T       *****************************************************
    // ***********************************************************************************************



        action drop() {
            ig_dprsr_md.drop_ctl = 0x1; // Drop packet.
        }
        action nop() {
        }
       
        action route_to_64(){
            //route to CPU NIC. on tofino model, it is veth250
            ig_tm_md.ucast_egress_port=64;
        }
        
        action mark_SEQ(){
            meta.pkt_type=PKT_TYPE_SEQ;
        }
        action mark_ACK(){
            meta.pkt_type=PKT_TYPE_ACK;
        }
        action drop_and_exit(){
            drop();exit;
        }
        
        // Decide packet is a data packet or an ACK
        
        table tb_decide_packet_type {
            key = {
                hdr.tcp.flags: ternary;
                hdr.ipv4.total_len: range;
                //hdr.ipv4.dst_addr: lpm; //use IP address to decide inside/outside
            }
            actions = {
                mark_SEQ;
                mark_ACK;
                drop_and_exit;
            }
            default_action = mark_SEQ();
            size = 512;
            const entries = {
                (TCP_FLAGS_S,_): mark_SEQ();
                (TCP_FLAGS_S+TCP_FLAGS_A,_): mark_ACK();
                (TCP_FLAGS_A, 0..80 ): mark_ACK();
                (TCP_FLAGS_A+TCP_FLAGS_P, 0..80 ): mark_ACK();
                (_,100..1600): mark_SEQ();
                (TCP_FLAGS_R,_): drop_and_exit();
                (TCP_FLAGS_F,_): drop_and_exit();
            }
        }
        
        // Calculate the expected ACK number for a data packet.
        // Formula: expected ACK=SEQ+(ipv4.total_len - 4*ipv4.ihl - 4*tcp.data_offset)
        // For SYN/SYNACK packets, add 1 to e_ack
        
        Hash<bit<32>>(HashAlgorithm_t.IDENTITY) copy32_1;
        Hash<bit<32>>(HashAlgorithm_t.IDENTITY) copy32_2;
        action compute_eack_1_(){
            meta.tmp_1=copy32_1.get({26w0 ++ hdr.ipv4.ihl ++ 2w0});
        }
        action compute_eack_2_(){
            meta.tmp_2=copy32_2.get({26w0 ++ hdr.tcp.data_offset ++ 2w0});
        }
        action compute_eack_3_(){
            meta.tmp_3=16w0 ++ hdr.ipv4.total_len;
        }
        action compute_eack_4_(){
            meta.total_hdr_len_bytes=(meta.tmp_1+meta.tmp_2);
        }
        action compute_eack_5_(){
            meta.total_body_len_bytes=meta.tmp_3 - meta.total_hdr_len_bytes;
        }
        action compute_eack_6_(){
            meta.expected_ack=hdr.tcp.seq_no + meta.total_body_len_bytes;
        }
        
        action compute_eack_last_if_syn(){
            meta.expected_ack=meta.expected_ack + 1;
            // could save 1 stage here by folding this into "++ 2w0" as "++ 2w1"
        }
        
        // Calculate 32-bit packet signature, to be stored into hash tables
        
        Hash<bit<32>>(HashAlgorithm_t.CRC32) crc32_1;
        Hash<bit<32>>(HashAlgorithm_t.CRC32) crc32_2;
        action get_pkt_signature_SEQ(){
            meta.pkt_signature=crc32_1.get({
                hdr.ipv4.src_addr, hdr.ipv4.dst_addr,
                hdr.tcp.src_port, hdr.tcp.dst_port,
                meta.expected_ack
            });
        }
        action get_pkt_signature_ACK(){
            meta.pkt_signature=crc32_2.get({
                hdr.ipv4.dst_addr,hdr.ipv4.src_addr, 
                hdr.tcp.dst_port,hdr.tcp.src_port, 
                hdr.tcp.ack_no
            });
        }
        
        // Calculate 16-bit hash table index
                
        Hash<bit<16>>(HashAlgorithm_t.CRC16) crc16_1;
        Hash<bit<16>>(HashAlgorithm_t.CRC16) crc16_2;
        action get_location_SEQ(){
            meta.hashed_location_1=crc16_1.get({
                //4w0,
                hdr.ipv4.src_addr, hdr.ipv4.dst_addr,
                hdr.tcp.src_port, hdr.tcp.dst_port,
                meta.expected_ack//,
                //4w0
            });
        }
        action get_location_ACK(){
            meta.hashed_location_1=crc16_2.get({
                //4w0,
                hdr.ipv4.dst_addr,hdr.ipv4.src_addr, 
                hdr.tcp.dst_port,hdr.tcp.src_port, 
                hdr.tcp.ack_no//,
                //4w0
            });
        }
        
        // Self-expiry hash table, each entry stores a signature and a timestamp
        
        #define TIMESTAMP ig_intr_md.ingress_mac_tstamp[31:0]
        #define TS_EXPIRE_THRESHOLD (50*1000*1000)
        //50ms
        #define TS_LEGITIMATE_THRESHOLD (2000*1000*1000)
        
        
        Register<paired_32bit,_>(32w65536) reg_table_1;
        //lo:signature, hi:timestamp
        
        RegisterAction<paired_32bit, _, bit<32>>(reg_table_1) table_1_insert= {  
            void apply(inout paired_32bit value, out bit<32> rv) {          
                rv = 0;                                                    
                paired_32bit in_value;                                          
                in_value = value;                 
                
                bool existing_timestamp_is_old = (TIMESTAMP-in_value.hi)>TS_EXPIRE_THRESHOLD;
                bool current_entry_empty = in_value.lo==0;
                
                if(existing_timestamp_is_old || current_entry_empty)
                {
                    value.lo=meta.pkt_signature;
                    value.hi=TIMESTAMP;
                    rv=1;
                }
            }                                                              
        };
        
        action exec_table_1_insert(){
            meta.table_1_read=table_1_insert.execute(meta.hashed_location_1);
        }
        
        RegisterAction<paired_32bit, _, bit<32>>(reg_table_1) table_1_tryRead= {  
            void apply(inout paired_32bit value, out bit<32> rv) {    
                rv=0;
                paired_32bit in_value;                                          
                in_value = value;     
                
                #define current_entry_matched (in_value.lo==meta.pkt_signature)
                #define timestamp_legitimate  ((TIMESTAMP-in_value.hi)<TS_LEGITIMATE_THRESHOLD)
                
                if(current_entry_matched && timestamp_legitimate)
                {
                    value.lo=0;
                    value.hi=0;
                    rv=in_value.hi;
                }
            }                                                              
        };
        
        action exec_table_1_tryRead(){
            meta.table_1_read=table_1_tryRead.execute(meta.hashed_location_1);
        }
        

    // ***********************************************************************************************
    // *************************     E N D   R T T       *********************************************
    // ***********************************************************************************************



    // ***********************************************************************************************
    // *************************        M E T E R I N G      *****************************************
    // ***********************************************************************************************
    action do_meter() {
        color = (bit<2>) bytes_meter.execute();  // Default color coding: 0 - Green,            1 - Yellow,            3- Red 
    }

    action inform_control_plane() {
        color = (bit<2>) bytes_meter.execute();
        ig_dprsr_md.digest_type=0;
    }
    //@idletime_precision(6)
    table metering {
       key = { meta.flow_id : exact; }
        actions = {
            do_meter;
            inform_control_plane;
        }
		size = 24000;
        meters = bytes_meter;
	    const default_action = inform_control_plane;
        idle_timeout         = true;
    }

    action route_to_CPU() {
	    ig_tm_md.ucast_egress_port=192;
    }

    table store_and_check_if_long_flow_informed {
        actions = {apply_read_store_long_flow;}
        const default_action = apply_read_store_long_flow;
    }

    table check_if_long_flow {
        actions = {apply_read_long_flow;}
        const default_action = apply_read_long_flow;
    }

    // ***********************************************************************************************
    // *************************  E N D   M E T E R I N G      ***************************************
    // ***********************************************************************************************

    
    Register<bit<32>, bit<16>>(65535) last_seq;
    RegisterAction<bit<32>, bit<16>, bit<32>>(last_seq) read_store_last_seq = {
        void apply(inout bit<32> register_data, out bit<32> result) {
            //if(meta.expected_ack != 0){
			if(hdr.tcp.seq_no + 65535 < register_data) {
				register_data = meta.expected_ack;
			}
			
			if(hdr.tcp.seq_no < register_data ) {
				result = register_data;
			} else
			{
				register_data = meta.expected_ack;
			}
			
        }
    };

    action exec_read_store_last_seq(){
        meta.lost=read_store_last_seq.execute(meta.flow_id);
    }


    Register<bit<32>, bit<1>>(1) total_retr;
    RegisterAction<bit<32>, bit<1>, bit<1>>(total_retr) update_total_retr = {
        void apply(inout bit<32> register_data) {
            if(meta.lost != 0) {
                register_data = register_data + 1;
            }
        }
    };
    action exec_update_total_retr(){
        update_total_retr.execute(0);
		
	}
    Register<bit<32>, bit<1>>(32) total_sent;
    RegisterAction<bit<32>, bit<1>, bit<32>>(total_sent) update_total_sent = {
        void apply(inout bit<32> register_data) {
            register_data = register_data + 1;
        }
    };
    action exec_update_total_sent(){
        update_total_sent.execute(0);
    }
	

	
	Register<bit<32>, bit<1>>(1) total_sent_before;
    RegisterAction<bit<32>, bit<1>, bit<32>>(total_sent_before) update_total_sent_before = {
        void apply(inout bit<32> register_data, out bit<32> result) {
			register_data = register_data + 1;
			result = register_data;
        }
    };
    action exec_update_total_sent_before(){
        meta.total_before = update_total_sent_before.execute(0);
    }
	
	
	Register<bit<32>, bit<1>>(1) total_sent_after;
    RegisterAction<bit<32>, bit<1>, bit<32>>(total_sent_after) update_total_sent_after = {
        void apply(inout bit<32> register_data, out bit<32> result) {
            register_data = register_data + 1;
			result = register_data;
        }
    };
    action exec_update_total_sent_after(){
        meta.total_after = update_total_sent_after.execute(0);
    }
	RegisterAction<bit<32>, bit<1>, bit<32>>(total_sent_before) read_total_sent_before = {
        void apply(inout bit<32> register_data, out bit<32> result) {
			result = register_data;
        }
    };
    action exec_read_total_sent_before(){
        meta.total_before = read_total_sent_before.execute(0);
    }
	
	Register<bit<32>, bit<1>>(1) report_reg;
    RegisterAction<bit<32>, bit<1>, bit<32>>(report_reg) update_report_reg = {
        void apply(inout bit<32> register_data, out bit<32> result) {
            if(register_data == 1000) {
				register_data = 0;
			} else {
				register_data = register_data + 1;
			}
			result = register_data;
        }
    };
    action exec_update_report_reg(){
        meta.report_loss = update_report_reg.execute(0);
		
    }
	
	
	Register<bit<32>, bit<1>>(1) last_report_timestamp;
	RegisterAction<bit<32>, bit<1>, bit<9>>(last_report_timestamp) update_last_report_timestamp = {
        void apply(inout bit<32> register_data, out bit<9> result) {
			 //if (ig_intr_md.ingress_mac_tstamp[31:0] - register_data > 1000000000) {
				register_data = ig_intr_md.ingress_mac_tstamp[31:0];
				result = 192;
			 //}
		}
    };
	action apply_update_last_report_timestamp() {
        ig_tm_md.ucast_egress_port = update_last_report_timestamp.execute(0);
    }






    Hash<bit<16>>(HashAlgorithm_t.CRC16) hash_udp;
    action apply_hash_udp() {
        meta.flow_id = hash_udp.get({
            //hdr.ipv4.src_addr,
            //hdr.ipv4.dst_addr,
            //hdr.ipv4.protocol,
            //hdr.udp.src_port
            //hdr.udp.dst_port,
			hdr.rtp.SSRC
			//hdr.rtp.sequence_number
        });
    }
    table calc_flow_id_udp {
        actions = {
            apply_hash_udp;
        }
        default_action = apply_hash_udp();
    }

    bit<32> result_sample;
	
	Register<bit<32>, bit<16>>(65535) last_timestamp;
	
	RegisterAction<bit<32>, bit<16>, bit<32>>(last_timestamp) update_last_timestamp = {
        void apply(inout bit<32> register_data) {
			register_data = ig_intr_md.ingress_mac_tstamp[31:0]; //[41:10];
		}
    };
	action apply_update_last_timestamp() {
        update_last_timestamp.execute(meta.flow_id);
    }

	RegisterAction<bit<32>, bit<16>, bit<32>>(last_timestamp) get_and_reset_timestamp = {
        void apply(inout bit<32> register_data, out bit<32> result) {
			if(register_data != 0){
				result = ig_intr_md.ingress_mac_tstamp[31:0] - register_data;
			} else {
				result = 111;
			}
			register_data = ig_intr_md.ingress_mac_tstamp[31:0];
			/*
			if(register_data == 0)  { 
                    register_data = ig_intr_md.ingress_mac_tstamp[31:0];
                    result = 111;
            } else if(ig_intr_md.ingress_mac_tstamp[31:0] > register_data && register_data != 0) { //[41:10];
				    result = ig_intr_md.ingress_mac_tstamp[31:0] - register_data;
            } 
			*/
				
		}
    };
	action apply_get_and_reset_timestamp() {
        result_sample = get_and_reset_timestamp.execute(meta.flow_id);
    }

	
	
	
    apply {
		
		hdr.tcp.in_port = ig_intr_md.ingress_port;
		
		
		if(ig_intr_md.ingress_port == 148) {
			exec_update_total_sent_before();
			
		} else if (ig_intr_md.ingress_port == 140) {
			exec_update_total_sent_after();
			exec_read_total_sent_before();
		} 
		
		
		
		
		//apply_update_last_report_timestamp();

		//route_to_CPU();
		if(ig_intr_md.ingress_port == 140) {
			exec_update_report_reg();
			//exec_read_total_sent_after();
			
			
		}
        if(hdr.ipv4.isValid() && hdr.tcp.isValid() && ig_intr_md.ingress_port != 148){ // && ig_intr_md.ingress_port != 156 ) {
			
			calc_flow_id.apply();
			calc_rev_flow_id.apply();
			

			apply_hash_0();
            apply_hash_1();
            apply_hash_2();
            apply_hash_3();

			exec_read_sketch0();
            exec_read_sketch1();
            exec_read_sketch2();
            exec_read_sketch3();
			
			if(counted_flow.apply().miss){
                if(ig_intr_md.ingress_port != 132 && meta.value_sketch0 == 1 && meta.value_sketch1 == 1 && meta.value_sketch2 == 1  && meta.value_sketch3 == 1) {
                    ig_dprsr_md.digest_type = 1;  
                }
            }
			/*
            if (metering.apply().hit) {                            // Get the color (green, yellow, red), or inform the control plane about a new flow joined
                if (color == 3) {                                    // We have a long flow
                    store_and_check_if_long_flow_informed.apply();     // Store long flow / check if we informed the control plane that this flow is RED (this is important so that we don't flood the control plane) 
                    if (stored == 0) {
                        ig_dprsr_md.digest_type=1;
                    }
                }
            }
			*/

                    // RTT calculation
                tb_decide_packet_type.apply();
                    
                // compute e_ack
                if(meta.pkt_type==PKT_TYPE_SEQ){
                    compute_eack_1_();
                    compute_eack_2_();
                    compute_eack_3_();
                    compute_eack_4_();
                    compute_eack_5_();
                    compute_eack_6_();
					//exec_read_store_last_seq();
                    if(hdr.tcp.flags==TCP_FLAGS_S){
                        compute_eack_last_if_syn();
                    } else {
						//if(meta.total_body_len_bytes > 0) {
                        exec_read_store_last_seq();
						//}
						if(meta.lost != 0) {
							ig_dprsr_md.digest_type = 3;
						}	
                    }
                }

                //get signature (after having eack)
        
                if(meta.pkt_type==PKT_TYPE_SEQ){
                    
                    get_pkt_signature_SEQ();
                    get_location_SEQ();
                }else{
                    get_pkt_signature_ACK();
                    get_location_ACK();
                }
                
                // insert into table if syn
                // read from table if ack
                
                // Insert or Read from hash table
                if(meta.pkt_type==PKT_TYPE_SEQ){
                    exec_table_1_insert();
					if(meta.report_loss == 1000) {
						ig_dprsr_md.digest_type = 4;
					}
                }else{
                    exec_table_1_tryRead();
                }

                               
                // send out report headers.
                if(meta.pkt_type==PKT_TYPE_SEQ){
                    exec_update_total_retr();
                }else{
                    if(meta.table_1_read==0){
                        meta.rtt=0;                        
                    }else{
                        meta.rtt = (TIMESTAMP-meta.table_1_read);
                        ig_dprsr_md.digest_type = 2;
                    }
                }

				exec_update_total_sent();
				//ig_dprsr_md.digest_type = 3;
            
			

            link_stats.count(0);
			
        } else if(hdr.ipv4.isValid() && hdr.udp.isValid()) {
			calc_flow_id_udp.apply();
			//meta.flow_id = 0; //hdr.rtp.sequence_number;
			if (ig_intr_md.ingress_port == 140) {
				apply_get_and_reset_timestamp();
				hdr.rtp.timestamp = result_sample;
				ig_tm_md.ucast_egress_port=192;
			}
		}
		

		if(ig_tm_md.ucast_egress_port != 192) {
			ig_tm_md.ucast_egress_port=148; // just to go to egress
		}
		
		
		
    }
	
	
	
}

    /*********************  D E P A R S E R  ************************/

control IngressDeparser(packet_out pkt,
    /* User */
    inout my_ingress_headers_t                       hdr,
    in    my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md)
{
    Digest<flow_digest_t>() new_flow_digest; 
    Digest<flow_digest_t>() new_long_flow_digest; 
    Digest<RTT_digest_t>()  rtt_sample_digest; 
    Digest<test_SEQ_t>()  test_SEQ; 
    Digest<queue_delay_sample_digest_t>()  queue_delay_sample_digest; 
    Digest<before_after_t>()  before_after; 

    apply {
        if(ig_dprsr_md.digest_type == 0) {
            new_flow_digest.pack({meta.flow_id, meta.rev_flow_id});
        } else if(ig_dprsr_md.digest_type == 1) {
            new_long_flow_digest.pack({meta.flow_id, meta.rev_flow_id});
        } else if(ig_dprsr_md.digest_type == 2) {
            rtt_sample_digest.pack({meta.flow_id, meta.rtt});
        } else if(ig_dprsr_md.digest_type == 3) {
            test_SEQ.pack({hdr.tcp.seq_no, meta.lost});
        } else if(ig_dprsr_md.digest_type == 4) {
            before_after.pack({meta.total_before, meta.total_after});
        } 
        pkt.emit(hdr);
    }
}


/*************************************************************************
 ****************  E G R E S S   P R O C E S S I N G   *******************
 *************************************************************************/

    /***********************  H E A D E R S  ************************/

struct my_egress_headers_t {
    ethernet_h   ethernet;
    ipv4_h       ipv4;
    tcp_h        tcp;
}

    /********  G L O B A L   E G R E S S   M E T A D A T A  *********/

struct my_egress_metadata_t {
	bit<32> packet_hash;
	bit<32> packet_queue_delay;		
	bit<16> flow_id;

}

    /***********************  P A R S E R  **************************/

parser EgressParser(packet_in        pkt,
    /* User */
    out my_egress_headers_t          hdr,
    out my_egress_metadata_t         meta,
    /* Intrinsic */
    out egress_intrinsic_metadata_t  eg_intr_md)
{
    /* This is a mandatory state, required by Tofino Architecture */
    state start {
        pkt.extract(eg_intr_md);
        transition parse_ethernet;
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.ether_type) {
            ETHERTYPE_IPV4:  parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            6: parse_tcp;
            default: accept;
        }
    }

    state parse_tcp {
        pkt.extract(hdr.tcp);
		transition accept;
    }
}

    /***************** M A T C H - A C T I O N  *********************/






control Egress(
    /* User */
    inout my_egress_headers_t                          hdr,
    inout my_egress_metadata_t                         meta,
    /* Intrinsic */
    in    egress_intrinsic_metadata_t                  eg_intr_md,
    in    egress_intrinsic_metadata_from_parser_t      eg_prsr_md,
    inout egress_intrinsic_metadata_for_deparser_t     eg_dprsr_md,
    inout egress_intrinsic_metadata_for_output_port_t  eg_oport_md)
{
	Hash<bit<16>>(HashAlgorithm_t.CRC16) hash;
    action apply_hash() {
        meta.flow_id = hash.get({
            hdr.ipv4.src_addr,
            hdr.ipv4.dst_addr,
            hdr.ipv4.protocol,
            hdr.tcp.src_port,
            hdr.tcp.dst_port
        });
    }
    table calc_flow_id {
        actions = {
            apply_hash;
        }
        const default_action = apply_hash();
    }
	
	
	// ------------------------- QUEUE DELAY--------------------------------------
	// ---------------------------------------------------------------------------
	
	Hash<bit<32>>(HashAlgorithm_t.CRC32) packet_hash;
    action apply_packet_hash() {
        meta.packet_hash = packet_hash.get({
            meta.flow_id,
			hdr.tcp.seq_no
        });
    }
    table calc_packet_hash {
        actions = {
            apply_packet_hash;
        }
        const default_action = apply_packet_hash();
    }
	Register<bit<32>, bit<17>>(100000) packets_timestamp;
    RegisterAction<bit<32>, bit<17>, bit<32>>(packets_timestamp) update_packets_timestamp = {
        void apply(inout bit<32> register_data) {
			//if(register_data == 0) {
				register_data = eg_prsr_md.global_tstamp[31:0];
			//}
		}
    };
    action exec_update_packets_timestamp(){
        update_packets_timestamp.execute(meta.packet_hash[16:0]);
    }
	RegisterAction<bit<32>, bit<17>, bit<32>>(packets_timestamp) calc_queue_delay_packet = {
        void apply(inout bit<32> register_data, out bit<32> result) {
            //result = eg_prsr_md.global_tstamp[30:15] - register_data;
			if(eg_prsr_md.global_tstamp[31:0] > register_data && eg_prsr_md.global_tstamp[31:0] - register_data < 200000000) {
				result = eg_prsr_md.global_tstamp[31:0] - register_data;
			} else {
				result = 0;
			}
        }
    };
    action exec_calc_queue_delay_packet(){
        meta.packet_queue_delay = calc_queue_delay_packet.execute(meta.packet_hash[16:0]);
    }
	
	// Averaging
	
	Lpf<value_t, bit<1>>(size=1) lpf_queue_delay_1;
	Lpf<value_t, bit<1>>(size=1) lpf_queue_delay_2;
	value_t lpf_queue_delay_input;
	value_t lpf_queue_delay_output_1;
	value_t lpf_queue_delay_output_2;

	
	
	Register<bit<32>, bit<1>>(1) queue_delays;
    RegisterAction<bit<32>, bit<1>, bit<32>>(queue_delays) update_queue_delays = {
        void apply(inout bit<32> register_data) {
            register_data = meta.packet_queue_delay;
        }
    };
    action exec_update_queue_delays(){
        update_queue_delays.execute(0);
    }


    apply {
		calc_flow_id.apply();
		calc_packet_hash.apply();
		if (hdr.tcp.in_port == 148) {
			exec_update_packets_timestamp();
		}
		else if(hdr.tcp.in_port == 140) {
			exec_calc_queue_delay_packet();
			if(meta.packet_queue_delay != 0) {
				lpf_queue_delay_input = (value_t)meta.packet_queue_delay;
				lpf_queue_delay_output_1 = lpf_queue_delay_1.execute(lpf_queue_delay_input, 0);
				lpf_queue_delay_output_2 = lpf_queue_delay_2.execute(lpf_queue_delay_output_1, 0);
				meta.packet_queue_delay = lpf_queue_delay_output_2;
				exec_update_queue_delays();
			}
		}
		eg_dprsr_md.drop_ctl = 0;
	
    }
}

    /*********************  D E P A R S E R  ************************/

control EgressDeparser(packet_out pkt,
    /* User */
    inout my_egress_headers_t                       hdr,
    in my_egress_metadata_t                      meta,
    /* Intrinsic */
    in    egress_intrinsic_metadata_for_deparser_t  eg_dprsr_md)
{
    apply {
        pkt.emit(hdr);
    }
}


/************ F I N A L   P A C K A G E ******************************/
Pipeline(
    IngressParser(),
    Ingress(),
    IngressDeparser(),
    EgressParser(),
    Egress(),
    EgressDeparser()
) pipe;

Switch(pipe) main;
